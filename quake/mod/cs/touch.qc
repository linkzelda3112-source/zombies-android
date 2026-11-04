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

#define K_TOUCH_A       600
#define K_TOUCH_B       603
#define K_MOUSE1_A      512

float t_down[T_MAXF];
float t_role[T_MAXF];
float t_have[T_MAXF];     // ya tenemos posicion de este dedo
float t_x[T_MAXF];
float t_y[T_MAXF];
float t_sx[T_MAXF];       // origen de la palanca (flotante)
float t_sy[T_MAXF];
float t_w, t_h;           // tamano virtual de pantalla
float t_stick_x, t_stick_y;
float t_impulse;
float t_inited;

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
};

// centro de cada boton segun el tamano de pantalla
vector(float role) Touch_BtnPos =
{
	if (role == R_FIRE)   return [t_w - 64, t_h - 74, 0];
	if (role == R_JUMP)   return [t_w - 54, t_h - 158, 0];
	if (role == R_RELOAD) return [t_w - 146, t_h - 50, 0];
	if (role == R_SWAP)   return [t_w - 150, t_h - 124, 0];
	if (role == R_BUY)    return [t_w - 222, t_h - 90, 0];
	return '0 0 0';
};

float(float role) Touch_BtnRadius =
{
	if (role == R_FIRE) return 44;
	if (role == R_JUMP) return 30;
	if (role == R_BUY) return 34;
	return 28;
};

float(float x, float y) Touch_Hit =
{
	local float r;
	local vector c;
	for (r = R_FIRE; r <= R_SWAP; r++)
	{
		c = Touch_BtnPos(r);
		if (vlen([x - c_x, y - c_y, 0]) < Touch_BtnRadius(r) + 10)
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
	if (r == R_RELOAD) t_impulse = 21;
	else if (r == R_BUY) t_impulse = 20;
	else if (r == R_SWAP) t_impulse = 10;
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
	t_have[d] = TRUE;

	if (!t_down[d]) return;
	if (t_role[d] == R_NONE)
	{
		Touch_Assign(d);
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
			dx = x - t_sx[d];
			dy = y - t_sy[d];
		}
	}
};

float(float ie, float p1, float p2, float p3) Touch_Event =
{
	local float d;
	d = p3;
	if (d < 0 || d >= T_MAXF) d = 0;

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
				t_role[d] = R_NONE;
				if (t_have[d])
					Touch_Assign(d);
			}
			else
			{
				t_down[d] = FALSE;
				t_role[d] = R_NONE;
				t_have[d] = FALSE;
			}
			return TRUE;
		}
	}
	return FALSE;
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
		if (t_role[i] == R_FIRE) fire = TRUE;
		else if (t_role[i] == R_JUMP) jump = TRUE;
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
	input_movevalues_x = input_movevalues_x - t_stick_y * 400;
	input_movevalues_y = input_movevalues_y + t_stick_x * 400;
	if (fire) input_buttons = input_buttons | 1;
	if (jump) input_buttons = input_buttons | 2;
	if (t_impulse)
	{
		input_impulse = t_impulse;
		t_impulse = 0;
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

	Touch_DrawBtn(R_FIRE, "gfx/touch_fire.tga", 0.5, '1 1 1');
	Touch_DrawBtn(R_JUMP, "gfx/touch_jump.tga", 0.45, '1 1 1');
	Touch_DrawBtn(R_RELOAD, "gfx/touch_reload.tga", 0.45, '1 1 1');
	Touch_DrawBtn(R_SWAP, "gfx/touch_swap.tga", 0.45, '1 1 1');
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
