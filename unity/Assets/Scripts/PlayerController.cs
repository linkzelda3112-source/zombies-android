using UnityEngine;

// Requiere un CharacterController en el jugador y la Main Camera como hija de "cameraPivot".
[RequireComponent(typeof(CharacterController))]
public class PlayerController : MonoBehaviour
{
    public Transform cameraPivot;      // Objeto vacío a la altura de la cabeza (~1.6 m)
    public Camera cam;
    public float moveSpeed = 5f;
    public float lookSensitivity = 0.15f;
    public bool thirdPerson = false;   // Cámbialo en el Inspector o con ToggleCamera()
    public Vector3 thirdPersonOffset = new Vector3(0.6f, 0.2f, -3f);

    CharacterController cc;
    float pitch;
    float yVel;

    void Awake() { cc = GetComponent<CharacterController>(); }

    void Update()
    {
        var input = TouchInput.I;
        if (input == null) return;

        // Rotación
        transform.Rotate(0f, input.Look.x * lookSensitivity, 0f);
        pitch = Mathf.Clamp(pitch - input.Look.y * lookSensitivity, -70f, 70f);
        cameraPivot.localRotation = Quaternion.Euler(pitch, 0f, 0f);

        // Movimiento
        Vector3 dir = transform.right * input.Move.x + transform.forward * input.Move.y;
        yVel = cc.isGrounded ? -1f : yVel - 20f * Time.deltaTime;
        cc.Move((dir * moveSpeed + Vector3.up * yVel) * Time.deltaTime);

        UpdateCamera();
    }

    void UpdateCamera()
    {
        Vector3 target = thirdPerson ? thirdPersonOffset : Vector3.zero;
        cam.transform.localPosition = Vector3.Lerp(cam.transform.localPosition, target, 12f * Time.deltaTime);
    }

    // Conéctalo a un botón de UI
    public void ToggleCamera() { thirdPerson = !thirdPerson; }
}
