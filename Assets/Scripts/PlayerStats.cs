using UnityEngine;
using UnityEngine.UI;

// Vida con regeneración (estilo CoD) y puntos para comprar.
public class PlayerStats : MonoBehaviour
{
    public static PlayerStats I;
    public int maxHealth = 100;
    public int points = 500;
    public float regenDelay = 5f;
    public float regenRate = 20f;      // vida por segundo
    public Text pointsText;
    public Text healthText;
    public GameObject gameOverPanel;

    float health;
    float lastHit;

    void Awake() { I = this; health = maxHealth; }

    void Update()
    {
        if (health > 0 && health < maxHealth && Time.time - lastHit > regenDelay)
            health = Mathf.Min(maxHealth, health + regenRate * Time.deltaTime);
        if (pointsText) pointsText.text = points.ToString();
        if (healthText) healthText.text = Mathf.CeilToInt(health).ToString();
    }

    public void TakeDamage(float dmg)
    {
        if (health <= 0) return;
        health -= dmg;
        lastHit = Time.time;
        if (health <= 0)
        {
            Time.timeScale = 0f;
            if (gameOverPanel) gameOverPanel.SetActive(true);
        }
    }

    public void AddPoints(int p) { points += p; }
    public bool Spend(int p) { if (points < p) return false; points -= p; return true; }
}
