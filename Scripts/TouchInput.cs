using UnityEngine;

// Entrada táctil: mitad izquierda = mover, mitad derecha = apuntar.
// Los botones de UI (disparar, recargar, comprar) llaman a los métodos públicos.
public class TouchInput : MonoBehaviour
{
    public static TouchInput I;
    public Vector2 Move;      // -1..1
    public Vector2 Look;      // delta de píxeles por frame
    public bool Fire;         // se mantiene mientras se presiona el botón

    int moveFinger = -1, lookFinger = -1;
    Vector2 moveStart;

    void Awake() { I = this; }

    void Update()
    {
        Look = Vector2.zero;
#if UNITY_EDITOR
        Move = new Vector2(Input.GetAxisRaw("Horizontal"), Input.GetAxisRaw("Vertical"));
        Look = new Vector2(Input.GetAxis("Mouse X"), Input.GetAxis("Mouse Y")) * 10f;
        Fire = Input.GetMouseButton(0);
        return;
#endif
        foreach (Touch t in Input.touches)
        {
            bool leftSide = t.position.x < Screen.width * 0.5f;
            if (t.phase == TouchPhase.Began)
            {
                if (leftSide && moveFinger == -1) { moveFinger = t.fingerId; moveStart = t.position; }
                else if (!leftSide && lookFinger == -1) lookFinger = t.fingerId;
            }
            if (t.fingerId == moveFinger)
            {
                Move = Vector2.ClampMagnitude((t.position - moveStart) / 100f, 1f);
                if (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled) { moveFinger = -1; Move = Vector2.zero; }
            }
            if (t.fingerId == lookFinger)
            {
                Look = t.deltaPosition;
                if (t.phase == TouchPhase.Ended || t.phase == TouchPhase.Canceled) lookFinger = -1;
            }
        }
    }

    // Conectar a botones de UI (EventTrigger: PointerDown / PointerUp)
    public void FireDown() { Fire = true; }
    public void FireUp() { Fire = false; }
}
