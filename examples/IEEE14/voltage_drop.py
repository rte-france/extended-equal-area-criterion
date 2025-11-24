import numpy as np

# ---------------------------
# Données d'entrée
# ---------------------------

# Ybus du réseau (complexe, p.u.) incluant les charges fictives aux extrémités de la ligne en défaut
Ybus = np.array([
    [10-30j, -5+15j, -5+15j],
    [-5+15j,  8-24j, -3+9j],
    [-5+15j, -3+9j,  8-24j]
], dtype=complex)

# Tensions pré-panne (V_pre) aux bus
V_pre = np.array([1.00+0j, 0.98-0.02j, 0.97-0.03j], dtype=complex)

# Bus de défaut (extrémité de la ligne en défaut)
fault_bus = 1

# ---------------------------
# Calcul linéaire vectorisé
# ---------------------------

# 1. Impédance de bus (Zbus)
Zbus = np.linalg.inv(Ybus)

# 2. Courant de défaut triphasé franc
I_f = V_pre[fault_bus] / Zbus[fault_bus, fault_bus]

# 3. Vecteur d'injection (tous les bus sauf défaut = 0)
I_inj = np.zeros(len(V_pre), dtype=complex)
I_inj[fault_bus] = I_f

# 4. Tensions post-défaut
V_post = V_pre - Zbus @ I_inj

# ---------------------------
# Affichage des résultats
# ---------------------------
print("Tensions post-défaut (p.u.) :")
for i, V in enumerate(V_post):
    print(f"Bus {i}: {V:.4f} ∠ {np.angle(V, deg=True):.2f}°")
