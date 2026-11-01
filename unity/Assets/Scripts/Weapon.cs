using System.Collections;
using UnityEngine;
using UnityEngine.UI;

// Arma con raycast desde el centro de la cámara. Ponla en el jugador.
public class Weapon : MonoBehaviour
{
    public Camera cam;
    public int damage = 25;
    public int headshotMultiplier = 2;
    public float fireRate = 0.12f;       // segundos entre disparos
    public float range = 80f;
    public int magSize = 30;
    public int reserveAmmo = 120;
    public float reloadTime = 1.8f;
    public Text ammoText;
    public ParticleSystem muzzleFlash;
    public AudioSource shotSound;

    int ammo;
    float nextShot;
    bool reloading;

    void Start() { ammo = magSize; }

    void Update()
    {
        if (ammoText) ammoText.text = ammo + " / " + reserveAmmo;
        if (reloading || TouchInput.I == null) return;

        if (TouchInput.I.Fire && Time.time >= nextShot)
        {
            if (ammo > 0) Shoot();
            else Reload();
        }
    }

    void Shoot()
    {
        nextShot = Time.time + fireRate;
        ammo--;
        if (muzzleFlash) muzzleFlash.Play();
        if (shotSound) shotSound.Play();

        if (Physics.Raycast(cam.transform.position, cam.transform.forward, out RaycastHit hit, range))
        {
            var z = hit.collider.GetComponentInParent<Zombie>();
            if (z != null)
            {
                bool head = hit.collider.name == "Head";
                z.TakeDamage(head ? damage * headshotMultiplier : damage, head);
            }
        }
    }

    // Conéctalo al botón de recarga
    public void Reload()
    {
        if (reloading || ammo == magSize || reserveAmmo <= 0) return;
        StartCoroutine(ReloadRoutine());
    }

    IEnumerator ReloadRoutine()
    {
        reloading = true;
        yield return new WaitForSeconds(reloadTime);
        int need = magSize - ammo;
        int take = Mathf.Min(need, reserveAmmo);
        ammo += take;
        reserveAmmo -= take;
        reloading = false;
    }

    public void AddAmmo(int n) { reserveAmmo += n; }
}
