import csv
import glob
import json
import paramiko
import stat
import os
import re
import shutil
from pathlib import Path
from deeac.__main__ import deeac

# -------------------------------------- CONFIGURATION -----------------------------------------------------------
# Parameters to launch parts of the script
create_ech_files = True
launch_load_flow = True
launch_eeac = True
# Parameters to create .ech files
json_file = "sensitivity.json"
file_ref = "fech.ech"
gen_ref = (
    "G  GEN    1 Y BUS    1   -9999.       0.    9999.    -100.       0.     100. "
    "V       0. BUS    1       1.       0.       0. Eolien "
)
format_gen = [ ("code1", 1), ("empty1", 2), ("name", 8), ("connect", 2), ("empty2", 1), ("bus", 8), ("pmin", 9),
               ("p", 9), ("pmax", 9), ("qmin", 9), ("q", 9), ("qmax", 9), ("reg", 2), ("voltage", 9), ("empty3", 1),
               ("bus_voltage", 8), ("code2", 27), ("empty4", 1), ("type", 8) ]
load_ref = "CH LOAD   2 Y BUS    1       0.       0.       0.       0.       0.       0.       0.       0."
format_load = [ ("code", 2), ("empty1", 1), ("name", 8), ("connect", 2), ("empty2", 1), ("bus", 8), ("code1", 18),
                ("p", 9), ("code2", 18), ("q", 9), ("code3", 18) ]
# Parameters to launch load flow
HOST = "10.132.136.89"
LOCAL_ECH_DIR = "ech"
LOCAL_LF_DIR = "lf"
REMOTE_TARGET_DIR = "/local/home/itesloc/tests_deeac/deeac/pierre"
REMOTE_ENV_FILE = "/local/home/itesloc/tests_deeac/eurostag/variables_environnement_pierre.txt"
RUN_SCRIPT_NAME = "run_loadflow.sh"
REMOTE_RUN_SCRIPT = os.path.join(REMOTE_TARGET_DIR, RUN_SCRIPT_NAME)
# Parameters to launch EEAC
csv_res = "synth.csv"
BASE_DIR = Path("output")
# ------------------------------------------------------------------------------------------------------------------

def parse_fixed_width(line, format_spec):
    """
    Split reference line in fields with fixed width.

    :param line: line to split.
    :param format_spec: field format.
    """
    pos = 0
    result = {}
    for field, width in format_spec:
        result[field] = line[pos:pos + width]
        pos += width
    return result


def build_line(values, format_spec):
    """
    Built a line with fixed width from dictionary.

    :param values: line to split.
    :param format_spec: field format.
    """
    parts = []
    for field, width in format_spec:
        val = str(values.get(field, "")).ljust(width)[:width]
        parts.append(val)
    return "".join(parts)


# Specific Constructions
gen_defaults = parse_fixed_width(gen_ref, format_gen)
load_defaults = parse_fixed_width(load_ref, format_load)


def build_gen_line(params):
    values = gen_defaults.copy()
    for k, v in params.items():
        if k in values:
            values[k] = str(v)
    values.setdefault("connect", "Y")
    return build_line(values, format_gen)


def build_load_line(params):
    values = load_defaults.copy()
    for k, v in params.items():
        if k in values:
            values[k] = str(v)
    values.setdefault("connect", "Y")
    return build_line(values, format_load)


def upload_dir(sftp, local_dir, remote_dir):
    """
    Upload files from local folder to remote folder.

    :param sftp: FTP connection (SFTPClient).
    :param local_dir: local folder (str).
    :param remote_dir: remote folder (str).
    """
    local_dir = os.path.abspath(local_dir)
    for root, dirs, files in os.walk(local_dir):
        for f_name in files:
            local_path = os.path.join(root, f_name)
            remote_path = remote_dir + "/" + f_name
            sftp.put(local_path, remote_path)


def download_lf_files(sftp, local_dir, remote_dir):
    """
    Download .lf files from remote folder to local folder.

    :param sftp: FTP connection (SFTPClient)
    :param local_dir: local folder (str).
    :param remote_dir: remote folder (str).
    """
    for entry in sftp.listdir_attr(remote_dir):
        name = entry.filename
        if name.lower().endswith(".lf") and stat.S_ISREG(entry.st_mode):
            remote_path = os.path.join(remote_dir, name).replace("\\", "/")
            local_path = os.path.join(local_dir, name)
            sftp.get(remote_path, local_path)


def run_remote_command(ssh, command):
    """
    Launch bash command in remote location.

    :param ssh: SSH connection (SSHClient).
    :param command: bash command (str).
    """
    full_cmd = f"bash -lc \'{command}\'"
    print(f"[remote] execution: {full_cmd}")
    stdin, stdout, stderr = ssh.exec_command(full_cmd, timeout=None)
    stdout.read().decode(errors="replace")


def remove_all_except_run_script(ssh, remote_dir, run_script_name):
    """
    Delete all files except "run_script_name" file.

    :param ssh: SSH connection (SSHClient).
    :param remote_dir: remote folder (str).
    :param run_script_name: script performing load flow (str).
    """
    cmd = (
        f'cd {remote_dir}; for f in *; do '
        f'[ \"$(basename \"$f\")\" = \"{run_script_name}\" ] && continue; rm -rf -- \"$f\"; done'
    )
    return run_remote_command(ssh, cmd)


def natural_key(s):
    """
    Extract numbers from string.

    :param s: string to decompose (str).
    """
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'(\d+)', str(s))]


def main():
    """
    Sensitivity analysis:
        - Create .ech files based on reference file
        - Launch load flow for each .ech files on remote Bullion network and download results
        - Launch EEAC on every situation
        - Save results on csv file
    """

    #------------------
    # Create .ech files
    #------------------

    if create_ech_files:
        print("Create .ech files")
        list(map(os.remove, glob.glob(f"{LOCAL_ECH_DIR}/*")))
        with open(json_file, "r") as f:
            data = json.load(f)

        for cfg in data["configurations"]:
            out_path = Path(LOCAL_ECH_DIR) / f"{cfg['name']}.ech"

            # Read .ech file
            with open(file_ref, "r", encoding="utf8") as f:
                content = f.read().rstrip("\n")
            lines_to_add = []

            # Generators
            for g in cfg.get("generators", []):
                lines_to_add.append(build_gen_line(g))

            # Loads
            for l in cfg.get("loads", []):
                lines_to_add.append(build_load_line(l))

            final_text = content + "\n" + "\n".join(lines_to_add) + "\n"
            out_path.write_text(final_text, encoding="utf8")

    # -------------------------------------
    # Launch load flow and download results
    # -------------------------------------

    if launch_load_flow:
        # SSH Connection
        print(f"Connection to {HOST} ...")
        username = input("Username:")
        password = input("Password:")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(HOST, username=username, password=password, timeout=10)
        transport = ssh.get_transport()
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Upload .ech files
        print("Upload .ech files ...")
        upload_dir(sftp if sftp else None, LOCAL_ECH_DIR, REMOTE_TARGET_DIR)

        # Source Eurostag environment and launch load flow on all .ech files
        print("Launch load flow ...")
        commands = f"source {REMOTE_ENV_FILE} && cd {REMOTE_TARGET_DIR} && {REMOTE_RUN_SCRIPT}"
        run_remote_command(ssh, commands)

        # Download all .lf files
        print("Download lf files ...")
        list(map(os.remove, glob.glob(f"{LOCAL_LF_DIR}/*")))
        download_lf_files(sftp if sftp else None, LOCAL_LF_DIR, REMOTE_TARGET_DIR)

        # Delete all files from remote folder except
        print("Delete temporary files ...")
        remove_all_except_run_script(ssh, REMOTE_TARGET_DIR, RUN_SCRIPT_NAME)

        # Close connection
        print("End SSH connection")
        sftp.close()
        ssh.close()

    # -----------------------------
    # Launch EEAC and write results
    # -----------------------------

    if launch_eeac:
        # Launch EEAC for each .seq files / .ech files / .lf files
        seq_files = sorted(glob.glob(f"*.seq"))
        ech_files = sorted(glob.glob(f"{LOCAL_ECH_DIR}/*.ech"))
        lf_files = sorted(glob.glob(f"{LOCAL_LF_DIR}/*.lf"))
        shutil.rmtree(BASE_DIR, ignore_errors=True)
        os.makedirs(BASE_DIR, exist_ok=True)
        for seq in seq_files:
            res1 = os.path.splitext(os.path.basename(seq))[0]
            for ech, lf in zip(ech_files, lf_files):
                res2 = os.path.splitext(os.path.basename(ech))[0]
                s = (f"--rewrite -t branch_1.json -e {ech} -d fdta.dta -l {lf} -s {seq} "
                     f"-o output/{res1}/{res2} -p 15 -v verbose")
                deeac(s.split())

        # Get all results in one csv file
        results = []
        for line_dir in sorted(BASE_DIR.glob("*")):
            for output_dir in sorted(line_dir.glob("*")):
                result_file = output_dir / "critical_cluster_results.json"
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Only one key in JSON (ex: "line_1-2")
                key = next(iter(data))
                content = data[key]
                # Check key existence
                if "critical_cluster" in content:
                    value1 = content["critical_cluster"]
                    if "CCT" in content:
                        value2 = content["CCT"]
                    elif content.get("status") == "ALWAYS STABLE":
                        value2 = "stable"
                    else:
                        value2 = "unknown"
                else:
                    value1 = "None"
                    value2 = "None"
                results.append((line_dir.name, output_dir.name, value1, value2))

        # Final Sort: sort number instead of string (default behavior)
        results.sort(key=lambda x: (natural_key(x[0]), natural_key(x[1])))

        # Save in CSV file
        with open(csv_res, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Line_Seq", "Output_Dir", "Critical_cluster", "CCT"])
            writer.writerows(results)


if __name__ == "__main__":
    main()
