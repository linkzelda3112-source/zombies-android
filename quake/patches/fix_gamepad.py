#!/usr/bin/env python3
"""Arregla las palancas/gatillos del mando en la actividad Java del motor.

El codigo original obtiene getMotionRange(int) y getAxisValue(int) por reflexion pero los invoca con
dos argumentos: siempre lanza excepcion (silenciada) y ningun eje del mando llega al juego.
Se reemplaza por llamadas directas e incluye los ejes alternativos (RX/RY, BRAKE/GAS)."""
import re, sys
p = sys.argv[1]
s = open(p, encoding="utf-8").read()

helper = '''
	private static float zmAxis(MotionEvent e, InputDevice d, int axis)
	{
		try
		{
			InputDevice.MotionRange r = d.getMotionRange(axis, e.getSource());
			if (r == null)
				return 0;
			float v = e.getAxisValue(axis, 0);
			float dead = Math.max(r.getFlat(), 0.08f);
			return (Math.abs(v) < dead) ? 0 : v;
		}
		catch (Exception ex)
		{
			return 0;
		}
	}
	private static float zmAxis2(MotionEvent e, InputDevice d, int a, int b)
	{
		float v = zmAxis(e, d, a);
		return (v != 0) ? v : zmAxis(e, d, b);
	}
'''
marker = "	private boolean motionEvent(MotionEvent event)"
assert marker in s
s = s.replace(marker, helper + marker, 1)

pat = re.compile(r"InputDevice dev = event\.getDevice\(\);\s*handleJoystickAxis\(event, dev, AXIS_X, 0\);.*?handleJoystickAxis\(event, dev, AXIS_RTRIGGER, 5\);", re.S)
new = '''InputDevice dev = event.getDevice();
			if (dev != null)
			{
				int did = event.getDeviceId();
				axis(did, 0, zmAxis(event, dev, 0));              // AXIS_X
				axis(did, 1, zmAxis(event, dev, 1));              // AXIS_Y
				axis(did, 2, zmAxis2(event, dev, 17, 23));        // LTRIGGER o BRAKE
				axis(did, 3, zmAxis2(event, dev, 11, 12));        // Z o RX
				axis(did, 4, zmAxis2(event, dev, 14, 13));        // RZ o RY
				axis(did, 5, zmAxis2(event, dev, 18, 22));        // RTRIGGER o GAS
			}'''
s, n = pat.subn(new, s, count=1)
assert n == 1, "no se encontro el bloque de ejes"
open(p, "w", encoding="utf-8").write(s)
print("fix_gamepad: ok")
