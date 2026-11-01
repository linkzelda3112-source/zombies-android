using UnityEngine;

// Compra de munición en la pared: acércate y toca el botón "Comprar" (llama a TryBuy).
public class WallBuy : MonoBehaviour
{
    public int cost = 500;
    public int ammoAmount = 90;
    public float useDistance = 2.5f;

    public void TryBuy()
    {
        var p = PlayerStats.I;
        if (p == null) return;
        if (Vector3.Distance(p.transform.position, transform.position) > useDistance) return;
        if (!p.Spend(cost)) return;
        p.GetComponent<Weapon>().AddAmmo(ammoAmount);
    }
}
