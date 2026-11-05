// ============================================================================
//  Controles tactiles propios (multitouch): palanca flotante a la izquierda,
//  arrastrar a la derecha para apuntar, botones grandes y disparo que tambien apunta.
// ============================================================================

#define T_MAXF      10
#define R_NONE      0
#define R_STICK     1
#define R_LOOK      2
#define R_FIRE      3
#define R_JUMP      4
#define R_RELOAD    5
#define R_BUY       6
#define R_SWAP      7
#define R_MELEE     8
#define R_SLIDE     9

#define K_TOUCH_A       600
#define K_TOUCH_B       603
#define K_MOUSE1_A      512

float t_down[T_MAXF];
float t_role[T_MAXF];
float t_rel[T_MAXF];      // se solto: se procesa en el siguiente comando de movimiento
float t_ox[T_MAXF];       // donde empezo el toque
float t_oy[T_MAXF];
float t_x[T_MAXF];
float t_y[T_MAXF];
float t_sx[T_MAXF];       // origen de la palanca (flotante)
float t_sy[T_MAXF];
float t_w, t_h;           // tamano virtual de pantalla
float t_stick_x, t_stick_y;
float t_act;               // botones de accion pendientes
float t_actframes;

void(float imp) Act =
{
	if (imp == 21) t_act = t_act | 16;
	else if (imp == 22) t_act = t_act | 64;
	else if (imp == 10) t_act = t_act | 128;
	else if (imp == 23 || imp == 20) t_act = t_act | 144;
	t_actframes = 4;
};
float t_inited;
string dbg_txt;
float dbg_t;
float t_mode;              // 0 = tactil, 1 = control (mando)

// estado del mando
float pad_lx, pad_ly, pad_rx, pad_ry, pad_lt, pad_rt;
float pad_a, pad_b, pad_rtk, pad_ltk;   // botones mantenidos (A, B, gatillos como tecla)
float pad_sprint;                        // L3 alterna correr

#define STICK_R     46
#define STICK_DEAD  0.14

void() Touch_Init =
{
	t_inited = TRUE;
	precache_pic("gfx/touch_fire.tga");
	precache_pic("gfx/touch_reload.tga");
	precache_pic("gfx/touch_buy.tga");
	precache_pic("gfx/touch_swap.tga");
	precache_pic("gfx/touch_jump.tga");
	precache_pic("gfx/touch_stick.tga");
	precache_pic("gfx/touch_melee.tga");
	precache_pic("gfx/touch_slide.tga");
};

// centro de cada boton segun el tamano de pantalla
vector(float role) Touch_BtnPos =
{
	if (role == R_FIRE)   return [t_w - 62, t_h - 70, 0];
	if (role == R_JUMP)   return [t_w - 62, t_h - 150, 0];
	if (role == R_RELOAD) return [t_w - 136, t_h - 46, 0];
	if (role == R_SWAP)   return [t_w - 38, 44, 0];
	if (role == R_MELEE)  return [t_w - 38, 98, 0];
	if (role == R_SLIDE)  return [t_w - 196, t_h - 62, 0];
	if (role == R_BUY)    return [t_w - 134, t_h - 108, 0];
	return '0 0 0';
};

float(float role) Touch_BtnRadius =
{
	if (role == R_FIRE) return 42;
	if (role == R_JUMP) return 28;
	if (role == R_BUY) return 30;
	if (role == R_SWAP || role == R_MELEE) return 22;
	if (role == R_SLIDE) return 26;
	return 26;
};

float(float x, float y) Touch_Hit =
{
	local float r;
	local vector c;
	for (r = R_FIRE; r <= R_SLIDE; r++)
	{
		c = Touch_BtnPos(r);
		if (vlen([x - c_x, y - c_y, 0]) < Touch_BtnRadius(r) + 6)
			return r;
	}
	return R_NONE;
};

float() Touch_StickBusy =
{
	local float i;
	for (i = 0; i < T_MAXF; i++)
		if (t_down[i] && t_role[i] == R_STICK) return TRUE;
	return FALSE;
};

void(float d) Touch_Assign =
{
	local float r;
	r = Touch_Hit(t_x[d], t_y[d]);
	if (r == R_NONE)
	{
		if (t_x[d] < t_w * 0.45 && !Touch_StickBusy())
		{
			r = R_STICK;
			t_sx[d] = t_x[d];
			t_sy[d] = t_y[d];
		}
		else
			r = R_LOOK;
	}
	t_role[d] = r;
	t_ox[d] = t_x[d];
	t_oy[d] = t_y[d];
};

void(float d, float dx, float dy) Touch_Look =
{
	local vector a;
	local float s;
	s = cvar("zm_looksens");
	if (s <= 0) s = 0.22;
	a = getviewprop(VF_CL_VIEWANGLES);
	a_y = a_y - dx * s;
	a_x = a_x + dy * s * 0.85;
	if (a_x > 80) a_x = 80;
	if (a_x < -80) a_x = -80;
	setviewprop(VF_CL_VIEWANGLES, a);
};

void(float d, float x, float y) Touch_Move =
{
	local float dx, dy, len, over;
	dx = x - t_x[d];
	dy = y - t_y[d];
	t_x[d] = x;
	t_y[d] = y;

	if (!t_down[d] || t_rel[d]) return;
	if (t_role[d] == R_NONE)
	{	// la primera posicion despues de tocar es la buena
		Touch_Assign(d);
		return;
	}
	// un boton de accion (recargar, comprar, cambiar) que se arrastra pasa a ser "mirar"
	if (t_role[d] >= R_RELOAD && t_role[d] <= R_MELEE)
	{
		if (vlen([x - t_ox[d], y - t_oy[d], 0]) > 14)
			t_role[d] = R_LOOK;
		return;
	}
	if (t_role[d] == R_LOOK || t_role[d] == R_FIRE)
		Touch_Look(d, dx, dy);
	else if (t_role[d] == R_STICK)
	{
		dx = x - t_sx[d];
		dy = y - t_sy[d];
		len = sqrt(dx * dx + dy * dy);
		if (len > STICK_R)
		{	// la base sigue al dedo si te pasas del radio
			over = (len - STICK_R) / len;
			t_sx[d] = t_sx[d] + dx * over;
			t_sy[d] = t_sy[d] + dy * over;
		}
	}
};

void() Pad_Reset =
{
	pad_lx = 0; pad_ly = 0; pad_rx = 0; pad_ry = 0; pad_lt = 0; pad_rt = 0;
	pad_a = 0; pad_b = 0; pad_rtk = 0; pad_ltk = 0; pad_sprint = 0;
};

void(float m) Touch_SetMode =
{
	local float i;
	if (m == t_mode) return;
	t_mode = m;
	if (m == 1)
	{
		for (i = 0; i < T_MAXF; i++) { t_down[i] = FALSE; t_rel[i] = FALSE; t_role[i] = R_NONE; }
	}
	else
		Pad_Reset();
};

// teclas/ejes del mando; devuelve TRUE si las usamos
float(float ie, float p1, float p2) Pad_Event =
{
	local float down;
	if (ie == IE_JOYAXIS)
	{
		if (p1 == 0) pad_lx = p2;
		else if (p1 == 1) pad_ly = p2;
		else if (p1 == 3) pad_rx = p2;
		else if (p1 == 4) pad_ry = p2;
		else if (p1 == 2) pad_lt = p2;
		else if (p1 == 5) pad_rt = p2;
		else return FALSE;
		if (fabs(p2) > 0.45) Touch_SetMode(1);
		return TRUE;
	}
	if (p1 < 816 || p1 > 839) return FALSE;
	down = (ie == IE_KEYDOWN);
	if (down) Touch_SetMode(1);
	if (p1 == K_GP_A) pad_a = down;
	else if (p1 == K_GP_B) pad_b = down;
	else if (p1 == K_GP_RTRIGGER) pad_rtk = down;
	else if (p1 == K_GP_LTRIGGER) pad_ltk = down;
	else if (down)
	{
		if (p1 == K_GP_X) Act(23);                         // usar / comprar / recargar
		else if (p1 == K_GP_Y) Act(10);                    // cambiar arma
		else if (p1 == K_GP_RTHUMB || p1 == K_GP_RSHOULDER) Act(22);   // cuchillada
		else if (p1 == K_GP_LSHOULDER) Act(21);            // recargar
		else if (p1 == K_GP_LTHUMB) pad_sprint = !pad_sprint;     // correr (alterna)
		else if (p1 == K_GP_DPAD_UP || p1 == K_GP_DPAD_RIGHT) Act(10);
	}
	return TRUE;
};

float(float ie, float p1, float p2, float p3) Touch_Event =
{
	local float d;
	d = p3;
	if (d < 0 || d >= T_MAXF) d = 0;

	// diagnostico en pantalla: ultima tecla/eje de mando recibido
	if (ie == IE_KEYDOWN && !(p1 >= K_TOUCH_A && p1 <= K_TOUCH_B) && p1 != K_MOUSE1_A)
	{
		dbg_txt = strcat("tecla ", ftos(p1));
		dbg_t = time;
	}
	if (ie == IE_JOYAXIS && fabs(p2) > 0.5)
	{
		dbg_txt = strcat("eje ", ftos(p1), " = ", ftos(rint(p2 * 100) / 100));
		dbg_t = time;
	}
	if (ie == IE_JOYAXIS)
		return Pad_Event(ie, p1, p2);
	if ((ie == IE_KEYDOWN || ie == IE_KEYUP) && p1 >= 816 && p1 <= 839)
		return Pad_Event(ie, p1, p2);

	// cualquier toque en pantalla vuelve a los controles tactiles
	if (ie == IE_MOUSEABS || ((ie == IE_KEYDOWN) && ((p1 >= K_TOUCH_A && p1 <= K_TOUCH_B) || p1 == K_MOUSE1_A)))
		Touch_SetMode(0);

	if (ie == IE_MOUSEABS)
	{
		Touch_Move(d, p1, p2);
		return TRUE;
	}
	if (ie == IE_KEYDOWN || ie == IE_KEYUP)
	{
		if ((p1 >= K_TOUCH_A && p1 <= K_TOUCH_B) || p1 == K_MOUSE1_A)
		{
			if (p1 == K_TOUCH_A + 1 || p1 == K_TOUCH_A + 2 || p1 == K_TOUCH_A + 3)
				return TRUE;	// gestos (tap, slide, long): los ignoramos
			if (ie == IE_KEYDOWN)
			{
				t_down[d] = TRUE;
				t_rel[d] = FALSE;
				t_role[d] = R_NONE;
			}
			else if (t_down[d])
				t_rel[d] = TRUE;	// se suelta despues de procesar este comando (asi un toque rapido no se pierde)
			return TRUE;
		}
	}
	return FALSE;
};

// mando: palanca izquierda mueve, derecha mira; gatillos y botones como en BO3
void() Pad_Frame =
{
	local float lx, ly, m, rx, ry, dt, s, ml;
	local vector a;
	ml = sqrt(pad_lx * pad_lx + pad_ly * pad_ly);
	lx = 0; ly = 0;
	if (ml > 0.2)
	{
		m = (ml - 0.2) / 0.8;
		if (m > 1) m = 1;
		lx = pad_lx / ml * m;
		ly = pad_ly / ml * m;
	}
	t_stick_x = lx;
	t_stick_y = ly;
	rx = pad_rx; ry = pad_ry;
	m = sqrt(rx * rx + ry * ry);
	if (m > 0.15)
	{
		s = (m - 0.15) / 0.85;
		if (s > 1) s = 1;
		s = s * s;
		rx = rx / m * s;
		ry = ry / m * s;
		dt = input_timelength;
		if (dt <= 0 || dt > 0.1) dt = 0.016;
		a = getviewprop(VF_CL_VIEWANGLES);
		a_y = a_y - rx * 230 * dt;
		a_x = a_x + ry * 170 * dt;
		if (a_x > 80) a_x = 80;
		if (a_x < -80) a_x = -80;
		setviewprop(VF_CL_VIEWANGLES, a);
		input_angles = a;
	}
	if (pad_rtk || pad_rt > 0.4) input_buttons = input_buttons | 1;
	if (pad_ltk || pad_lt > 0.4) input_buttons = input_buttons | 32;
	if (pad_a) input_buttons = input_buttons | 2;
	if (pad_b) input_buttons = input_buttons | 8;
	// correr como en BO3: L3 lo activa; se corta al soltar la palanca, disparar, apuntar, recargar o dar cuchillada
	if (pad_sprint)
	{
		if (ly < -0.3 && !(input_buttons & 33) && !(t_act & 208))
			input_buttons = input_buttons | 4;
		else
			pad_sprint = FALSE;
	}
};

// lo llama el motor en cada comando de movimiento: aqui metemos movimiento y botones
void() CSQC_Input_Frame =
{
	local float i, fire, jump, dx, dy, len, mag;
	fire = FALSE;
	jump = FALSE;
	t_stick_x = 0;
	t_stick_y = 0;
	for (i = 0; i < T_MAXF; i++)
	{
		if (!t_down[i]) continue;
		if (t_role[i] == R_NONE) Touch_Assign(i);	// no llego posicion nueva: usamos la ultima conocida
		if (t_role[i] == R_FIRE) fire = TRUE;
		else if (t_role[i] == R_JUMP) jump = TRUE;
		else if (t_role[i] == R_SLIDE) input_buttons = input_buttons | 8;
		else if (t_role[i] == R_STICK)
		{
			dx = t_x[i] - t_sx[i];
			dy = t_y[i] - t_sy[i];
			len = sqrt(dx * dx + dy * dy);
			mag = len / STICK_R;
			if (mag > 1) mag = 1;
			if (mag > STICK_DEAD)
			{
				mag = (mag - STICK_DEAD) / (1 - STICK_DEAD);
				t_stick_x = dx / len * mag;
				t_stick_y = dy / len * mag;
			}
		}
	}
	// botones de accion: se activan al soltar (si no se arrastraron)
	for (i = 0; i < T_MAXF; i++)
	{
		if (!t_down[i] || !t_rel[i]) continue;
		if (t_role[i] == R_RELOAD) Act(21);
		else if (t_role[i] == R_BUY) Act(20);
		else if (t_role[i] == R_SWAP) Act(10);
		else if (t_role[i] == R_MELEE) Act(22);
	}
	if (t_mode == 1)
		Pad_Frame();
	else if (t_stick_y < -0.5 && fabs(t_stick_x) < 0.6 && sqrt(t_stick_x * t_stick_x + t_stick_y * t_stick_y) > 0.93)
		input_buttons = input_buttons | 4;       // palanca a tope hacia adelante = correr
	input_movevalues_x = input_movevalues_x - t_stick_y * 400;
	input_movevalues_y = input_movevalues_y + t_stick_x * 400;
	if (fire) input_buttons = input_buttons | 1;
	if (jump) input_buttons = input_buttons | 2;
	// acciones por botones (mas fiable que los impulsos): recargar=16, cuchillada=64, cambiar=128, usar/comprar=16+128
	if (t_actframes > 0)
	{
		input_buttons = input_buttons | t_act;
		t_actframes = t_actframes - 1;
		if (t_actframes <= 0) t_act = 0;
	}
	// ya se aplico lo ultimo de los dedos que se soltaron
	for (i = 0; i < T_MAXF; i++)
	{
		if (t_down[i] && t_rel[i])
		{
			t_down[i] = FALSE;
			t_rel[i] = FALSE;
			t_role[i] = R_NONE;
		}
	}
};

float(float role) Touch_Pressed =
{
	local float i;
	for (i = 0; i < T_MAXF; i++)
		if (t_down[i] && t_role[i] == role) return TRUE;
	return FALSE;
};

void(float role, string pic, float a, vector rgb) Touch_DrawBtn =
{
	local vector c;
	local float r;
	c = Touch_BtnPos(role);
	r = Touch_BtnRadius(role);
	if (Touch_Pressed(role)) { a = 0.9; r = r * 1.08; }
	drawpic([c_x - r, c_y - r, 0], pic, [r * 2, r * 2, 0], rgb, a, 0);
};

void(vector viewsize, float buyready) Touch_Draw =
{
	local float i;
	local vector base;
	if (!t_inited) Touch_Init();
	t_w = viewsize_x;
	t_h = viewsize_y;
	if (t_mode == 1) return;   // con mando en uso no se dibujan los controles tactiles

	Touch_DrawBtn(R_FIRE, "gfx/touch_fire.tga", 0.5, '1 1 1');
	Touch_DrawBtn(R_JUMP, "gfx/touch_jump.tga", 0.45, '1 1 1');
	Touch_DrawBtn(R_RELOAD, "gfx/touch_reload.tga", 0.45, '1 1 1');
	Touch_DrawBtn(R_SWAP, "gfx/touch_swap.tga", 0.45, '1 1 1');
	Touch_DrawBtn(R_MELEE, "gfx/touch_melee.tga", 0.45, '1 1 1');
	Touch_DrawBtn(R_SLIDE, "gfx/touch_slide.tga", 0.45, '1 1 1');
	if (buyready)
		Touch_DrawBtn(R_BUY, "gfx/touch_buy.tga", 0.95, '1 1 0.4');
	else
		Touch_DrawBtn(R_BUY, "gfx/touch_buy.tga", 0.2, '1 1 1');

	// palanca flotante (solo mientras esta activa); si no, una pista tenue
	for (i = 0; i < T_MAXF; i++)
	{
		if (t_down[i] && t_role[i] == R_STICK)
		{
			drawpic([t_sx[i] - STICK_R, t_sy[i] - STICK_R, 0], "gfx/touch_stick.tga", [STICK_R * 2, STICK_R * 2, 0], '1 1 1', 0.35, 0);
			base = [t_x[i], t_y[i], 0];
			drawpic([base_x - 20, base_y - 20, 0], "gfx/touch_stick.tga", [40, 40, 0], '1 1 1', 0.75, 0);
			return;
		}
	}
	drawpic([t_w * 0.12 - STICK_R, t_h - 80 - STICK_R, 0], "gfx/touch_stick.tga", [STICK_R * 2, STICK_R * 2, 0], '1 1 1', 0.12, 0);
};

// el motor llama a esta funcion con cada evento de entrada
float(float ie, float p1, float p2, float p3) CSQC_InputEvent =
{
	return Touch_Event(ie, p1, p2, p3);
};

void(vector viewsize) Touch_Debug =
{
	if (dbg_txt != "" && time - dbg_t < 3)
		drawstring([viewsize_x * 0.5 - 40, 6, 0], dbg_txt, '7 7 0', '0.6 1 0.6', 0.8, 0);
};
