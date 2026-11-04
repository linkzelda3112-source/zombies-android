// ============================================================================
//  HUD del lado cliente (CSQC): vida, puntos, ronda, municion, avisos
//  Lee los valores que manda el servidor con clientstat/globalstat (world.qc)
// ============================================================================

#define ST_POINTS   (STAT_USER + 0)
#define ST_CLIP     (STAT_USER + 1)
#define ST_RESERVE  (STAT_USER + 2)
#define ST_WEAPON   (STAT_USER + 3)
#define ST_HIT      (STAT_USER + 4)
#define ST_HURT     (STAT_USER + 5)
#define ST_PROMPT   (STAT_USER + 6)
#define ST_KILLS    (STAT_USER + 7)
#define ST_RELOAD   (STAT_USER + 8)
#define ST_MAXHP    (STAT_USER + 9)
#define ST_ROUND    (STAT_USER + 10)
#define ST_LEFT     (STAT_USER + 11)
#define ST_STATE    (STAT_USER + 12)
#define ST_GAMEOVER (STAT_USER + 13)

float hud_round;       // ultima ronda vista (para anunciar la nueva)
float hud_round_t;     // cuando cambio
float hud_points;      // ultimos puntos vistos
float hud_gain;        // ganancia reciente (para el "+60")
float hud_gain_t;
float hud_hit;
float hud_hit_t;
float hud_hurt;
float hud_hurt_t;

string(float w) HudWeaponName =
{
	if (w == 1) return "KUDA SMG";
	if (w == 2) return "TRENCH GUN";
	if (w == 3) return "G-43 RIFLE";
	return "M1911";
};

// texto centrado en x
void(vector viewsize, float y, string text, vector size, vector rgb, float alpha) HudCenter =
{
	local float w;
	w = stringwidth(text, FALSE, size);
	drawstring([(viewsize_x - w) * 0.5, y, 0], text, size, rgb, alpha, 0);
};

// texto alineado a la derecha
void(float xright, float y, string text, vector size, vector rgb, float alpha) HudRight =
{
	local float w;
	w = stringwidth(text, FALSE, size);
	drawstring([xright - w, y, 0], text, size, rgb, alpha, 0);
};

void(vector viewsize, vector c, float a) HudVignette =
{
	local float t;
	t = viewsize_y * 0.12;
	drawfill('0 0 0', [viewsize_x, t, 0], c, a, 0);
	drawfill([0, viewsize_y - t, 0], [viewsize_x, t, 0], c, a, 0);
	drawfill([0, t, 0], [t * 0.7, viewsize_y - 2 * t, 0], c, a, 0);
	drawfill([viewsize_x - t * 0.7, t, 0], [t * 0.7, viewsize_y - 2 * t, 0], c, a, 0);
};

void(vector viewsize, float scoresshown) CSQC_DrawHud =
{
	local float pts, clip, res, wep, hit, hurt, kills, rnd, left, state, over, hp;
	local float a, t, w, x, y, mhp;
	local string prompt;
	local vector c;

	pts = getstatf(ST_POINTS);
	clip = getstatf(ST_CLIP);
	res = getstatf(ST_RESERVE);
	wep = getstatf(ST_WEAPON);
	hit = getstatf(ST_HIT);
	hurt = getstatf(ST_HURT);
	kills = getstatf(ST_KILLS);
	rnd = getstatf(ST_ROUND);
	left = getstatf(ST_LEFT);
	state = getstatf(ST_STATE);
	over = getstatf(ST_GAMEOVER);
	hp = getstatf(STAT_HEALTH);
	mhp = getstatf(ST_MAXHP);
	if (mhp < 100) mhp = 100;
	prompt = getstats(ST_PROMPT);

	// ---- detectar cambios (anuncio de ronda, ganancia de puntos, impactos, danos)
	if (rnd != hud_round)
	{
		hud_round = rnd;
		hud_round_t = time;
	}
	if (pts != hud_points)
	{
		if (pts > hud_points)
		{
			hud_gain = pts - hud_points;
			hud_gain_t = time;
		}
		hud_points = pts;
	}
	if (hit != hud_hit)
	{
		hud_hit = hit;
		hud_hit_t = time;
	}
	if (hurt != hud_hurt)
	{
		hud_hurt = hurt;
		hud_hurt_t = time;
	}

	// ---- flash rojo al recibir dano y viñeta con poca vida
	a = 1 - (time - hud_hurt_t) * 1.6;
	if (a > 0 && hud_hurt_t > 0) HudVignette(viewsize, '0.8 0 0', a * 0.55);
	if (hp > 0 && hp < 45) HudVignette(viewsize, '0.6 0 0', (45 - hp) / 45 * 0.4);

	// ---- mira y marcador de impacto
	x = viewsize_x * 0.5;
	y = viewsize_y * 0.5;
	if (!over)
	{
		drawfill([x - 9, y - 0.5, 0], '5 1 0', '1 1 1', 0.8, 0);
		drawfill([x + 4, y - 0.5, 0], '5 1 0', '1 1 1', 0.8, 0);
		drawfill([x - 0.5, y - 9, 0], '1 5 0', '1 1 1', 0.8, 0);
		drawfill([x - 0.5, y + 4, 0], '1 5 0', '1 1 1', 0.8, 0);
		a = 1 - (time - hud_hit_t) * 6;
		if (a > 0 && hud_hit_t > 0)
		{
			drawfill([x - 8, y - 8, 0], '3 3 0', '1 0.2 0.2', a, 0);
			drawfill([x + 5, y - 8, 0], '3 3 0', '1 0.2 0.2', a, 0);
			drawfill([x - 8, y + 5, 0], '3 3 0', '1 0.2 0.2', a, 0);
			drawfill([x + 5, y + 5, 0], '3 3 0', '1 0.2 0.2', a, 0);
		}
	}

	// ---- vida (abajo a la izquierda)
	w = 110;
	drawfill([14, viewsize_y - 22, 0], [w + 4, 10, 0], '0 0 0', 0.55, 0);
	c = '0.2 0.9 0.2';
	if (hp < mhp * 0.6) c = '0.95 0.8 0.1';
	if (hp < mhp * 0.3) c = '0.95 0.15 0.1';
	if (hp > 0) drawfill([16, viewsize_y - 20, 0], [w * hp / mhp, 6, 0], c, 0.9, 0);
	if (mhp > 100) drawstring([14, viewsize_y - 34, 0], "JUGGER-NOG", '6 6 0', '0.9 0.2 0.2', 0.9, 0);

	// ---- ronda (numero grande rojo, abajo a la izquierda)
	drawstring([14, viewsize_y - 62, 0], ftos(rnd), '30 30 0', '0.75 0.05 0.05', 0.95, 0);
	drawstring([14, viewsize_y - 74, 0], "ROUND", '8 8 0', '0.9 0.9 0.9', 0.7, 0);

	// ---- puntos (izquierda, centro)
	drawstring([14, viewsize_y * 0.5 + 20, 0], ftos(pts), '14 14 0', '1 0.9 0.3', 1, 0);
	a = 1 - (time - hud_gain_t) * 1.2;
	if (a > 0 && hud_gain_t > 0)
		drawstring([14, viewsize_y * 0.5 + 38 + (1 - a) * 14, 0], strcat("+", ftos(hud_gain)), '10 10 0', '1 1 0.6', a, 0);

	// ---- municion (abajo a la derecha)
	HudRight(viewsize_x - 14, viewsize_y - 64, HudWeaponName(wep), '8 8 0', '0.9 0.9 0.9', 0.85);
	HudRight(viewsize_x - 14, viewsize_y - 50, strcat(ftos(clip), " / ", ftos(res)), '14 14 0', '1 1 1', 1);
	if (getstatf(ST_RELOAD))
		HudRight(viewsize_x - 14, viewsize_y - 80, "RELOADING", '8 8 0', '1 0.8 0.2', 0.9);
	else if (clip <= 0 && res <= 0)
		HudRight(viewsize_x - 14, viewsize_y - 80, "NO AMMO", '8 8 0', '1 0.2 0.2', 0.9);

	// ---- zombies que faltan (arriba a la derecha)
	if (left > 0)
		HudRight(viewsize_x - 14, 14, strcat("ZOMBIES  ", ftos(left)), '8 8 0', '0.9 0.6 0.6', 0.85);

	// ---- aviso de compra
	if (prompt != "" && !over)
	{
		w = stringwidth(prompt, FALSE, '10 10 0');
		drawfill([(viewsize_x - w) * 0.5 - 8, viewsize_y * 0.62 - 4, 0], [w + 16, 18, 0], '0 0 0', 0.55, 0);
		HudCenter(viewsize, viewsize_y * 0.62, prompt, '10 10 0', '1 1 1', 1);
		HudCenter(viewsize, viewsize_y * 0.62 + 20, "tap BUY", '8 8 0', '0.8 0.8 0.8', 0.8);
	}

	// ---- anuncio de ronda
	t = time - hud_round_t;
	if (rnd > 0 && t < 3.5 && !over)
	{
		a = 1;
		if (t > 2.5) a = 1 - (t - 2.5);
		HudCenter(viewsize, viewsize_y * 0.28, strcat("ROUND ", ftos(rnd)), '30 30 0', '0.85 0.05 0.05', a);
	}
	else if (rnd == 0 && state <= 1 && !over)
		HudCenter(viewsize, viewsize_y * 0.28, "GET READY", '24 24 0', '0.9 0.9 0.9', 0.9);

	// ---- fin de la partida
	if (over)
	{
		drawfill('0 0 0', viewsize, '0 0 0', 0.6, 0);
		HudCenter(viewsize, viewsize_y * 0.34, "GAME OVER", '36 36 0', '0.85 0.05 0.05', 1);
		HudCenter(viewsize, viewsize_y * 0.34 + 50, strcat("YOU SURVIVED ", ftos(rnd), " ROUNDS"), '12 12 0', '1 1 1', 1);
		HudCenter(viewsize, viewsize_y * 0.34 + 70, strcat("KILLS ", ftos(kills)), '10 10 0', '0.9 0.9 0.9', 1);
	}
};

// el motor la llama en cada frame de entrada; no necesitamos tocar nada
void() CSQC_Input_Frame =
{
};
