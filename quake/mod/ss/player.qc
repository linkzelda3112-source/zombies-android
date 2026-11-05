// ============================================================================
//  Jugador: aparicion, entrada, regeneracion, dano, muerte, bot de pruebas
// ============================================================================

void(entity p) player_die =
{
	p.deadflag = DEAD_DEAD;
	p.health = 0;
	p.takedamage = DAMAGE_NO;
	p.solid = SOLID_NOT;
	p.movetype = MOVETYPE_NONE;
	p.velocity = '0 0 0';
	p.view_ofs = '0 0 -8';
	p.weaponmodel = "";
	p.zm_prompt = "";
	sound(p, CHAN_VOICE, "player/death.wav", 1, ATTN_NORM);
	bprint(strcat("ZM: player died on round ", ftos(zm_round), "\n"));
};

void(entity targ, entity attacker, float dmg, float head) Hurt =
{
	if (targ.classname == "zombie")
	{
		if (targ.health <= 0) return;
		targ.health = targ.health - dmg;
		if (attacker.classname == "player")
		{
			attacker.zm_points = attacker.zm_points + 10;
			attacker.zm_hit = attacker.zm_hit + 1;
		}
		if (targ.health <= 0)
			zombie_die(targ, attacker, head);
		else if (random() < 0.25)
			sound(targ, CHAN_VOICE, "zombie/pain.wav", 1, ATTN_NORM);
		return;
	}
	if (targ.classname == "player")
	{
		if (targ.deadflag != DEAD_NO) return;
		if (zm_test == 2) return;
		targ.health = targ.health - dmg;
		targ.zm_lasthurt = time;
		targ.zm_hurt = targ.zm_hurt + 1;
		if (targ.health <= 0)
			player_die(targ);
		else
			sound(targ, CHAN_VOICE, "player/pain.wav", 1, ATTN_NORM);
	}
};

// ---- bot solo para pruebas automaticas (cvar zm_test) -----------------------
void() bot_think =
{
	local entity z, best;
	local float d, bd;
	local vector tgt, ang;

	if (zm_test != 2) return;

	// munición infinita
	SetRes(self, self.zm_cur, 999);

	// prueba de compras: en cuanto alcanza compra el SMG en la pared
	if (self.zm_points >= 1000 && !(self.zm_own & 2))
		self.impulse = 20;
	if (GetClip(self, self.zm_cur) <= 0 && !self.zm_reload_end)
		self.impulse = 21;

	bd = 999999;
	best = world;
	z = find(world, classname, "zombie");
	while (z)
	{
		if (z.health > 0)
		{
			d = vlen(z.origin - self.origin);
			if (d < bd)
			{
				bd = d;
				best = z;
			}
		}
		z = find(z, classname, "zombie");
	}

	if (best != world)
	{
		tgt = best.origin + '0 0 22';
		ang = vectoangles(tgt - (self.origin + self.view_ofs));
		ang_x = 0 - ang_x;
		self.v_angle = ang;
		self.angles_y = ang_y;
		// pulsa el gatillo para armas semiautomaticas
		if (self.button0)
			self.button0 = 0;
		else
			self.button0 = 1;
	}
	else
		self.button0 = 0;
};

// ---- ciclo de vida del cliente ---------------------------------------------
void() SetNewParms =
{
};

void() SetChangeParms =
{
};

void() ClientKill =
{
};

void() ClientConnect =
{
	bprint(strcat("ZM: ", self.netname, " joined\n"));
};

void() ClientDisconnect =
{
	bprint(strcat("ZM: ", self.netname, " left\n"));
};

void() PutClientInServer =
{
	local entity spot;

	spot = find(world, classname, "info_player_start");

	self.classname = "player";
	self.health = 100;
	self.max_health = 100;
	self.takedamage = DAMAGE_AIM;
	self.solid = SOLID_SLIDEBOX;
	self.movetype = MOVETYPE_WALK;
	self.flags = FL_CLIENT;
	self.deadflag = DEAD_NO;
	self.maxspeed = 280;
	self.gravity = 1;
	self.view_ofs = '0 0 22';
	self.zm_stance = 0;
	self.zm_sprinting = 0;
	self.zm_slide_end = 0;
	self.velocity = '0 0 0';
	self.effects = 0;
	self.model = "";
	setsize(self, '-16 -16 -24', '16 16 32');
	if (spot != world)
	{
		setorigin(self, spot.origin + '0 0 1');
		self.angles = spot.angles;
	}
	self.fixangle = TRUE;

	// equipo inicial: pistola
	self.zm_points = 500;
	self.zm_kills = 0;
	self.zm_own = 1;
	self.zm_cur = W_PISTOL;
	W_Load(W_PISTOL);
	SetClip(self, W_PISTOL, w_clip);
	SetRes(self, W_PISTOL, w_resmax - w_clip);
	self.zm_reload_end = 0;
	self.zm_nextshot = 0;
	self.zm_lasthurt = 0;
	W_Equip(self);
};

// ---- movimiento tipo BO3: correr, agacharse, deslizarse (B), cuchillada ------------
void(entity p, float st) Stance_Set =
{
	if (st == p.zm_stance) return;
	if (st == 0)
	{
		tracebox(p.origin, '-16 -16 -24', '16 16 32', p.origin, FALSE, p);
		if (trace_startsolid || trace_allsolid) return;   // no hay espacio para levantarse
		setsize(p, '-16 -16 -24', '16 16 32');
		p.view_ofs = '0 0 22';
	}
	else
	{
		setsize(p, '-16 -16 -24', '16 16 8');
		p.view_ofs = '0 0 4';
	}
	p.zm_stance = st;
};

void(entity p) Move_Update =
{
	local float spd, ground, press, v, t;
	local vector d;
	ground = p.flags & FL_ONGROUND;
	spd = vlen([p.velocity_x, p.velocity_y, 0]);
	press = p.button4 && !p.zm_b4;
	p.zm_b4 = p.button4;

	// correr: boton de sprint + moviendose hacia adelante, de pie
	p.zm_sprinting = FALSE;
	if (p.button3 && p.zm_stance == 0 && ground && spd > 200 && !p.zm_reload_end)
		p.zm_sprinting = TRUE;

	// B: deslizarse si vas corriendo; si no, agacharse mientras lo mantienes
	if (press && p.zm_sprinting && time > p.zm_slide_end + 0.3)
	{
		makevectors(p.v_angle);
		d = [p.velocity_x, p.velocity_y, 0];
		p.zm_slidedir = normalize(d);
		p.zm_slide_start = time;
		p.zm_slide_end = time + 0.85;
		Stance_Set(p, 2);
	}
	if (p.zm_stance == 2)
	{
		if (time >= p.zm_slide_end || !ground || p.button2)
		{
			if (p.button4 && ground) Stance_Set(p, 1);
			else Stance_Set(p, 0);
			if (p.zm_stance == 2) p.zm_slide_end = time;
		}
		else
		{
			t = (p.zm_slide_end - time) / 0.85;
			v = 200 + 330 * t * t;
			p.velocity_x = p.zm_slidedir_x * v;
			p.velocity_y = p.zm_slidedir_y * v;
		}
	}
	else if (p.button4 && ground)
		Stance_Set(p, 1);
	else if (p.zm_stance == 1 && !p.button4)
		Stance_Set(p, 0);

	if (p.zm_stance == 2) p.maxspeed = 100;
	else if (p.zm_stance == 1) p.maxspeed = 130;
	else if (p.zm_sprinting) p.maxspeed = 380;
	else if (p.button6) p.maxspeed = 200;
	else p.maxspeed = 280;
};

void(entity p) Melee =
{
	local vector src;
	if (time < p.zm_nextmelee || p.zm_reload_end) return;
	p.zm_nextmelee = time + 0.6;
	p.punchangle = '-3 0 0';
	makevectors(p.v_angle);
	src = p.origin + p.view_ofs;
	traceline(src, src + v_forward * 72, FALSE, p);
	if (trace_ent != world && trace_ent.classname == "zombie" && trace_ent.takedamage)
	{
		te_blood(trace_endpos, '0 0 0', 40);
		Hurt(trace_ent, p, 150, FALSE);
		sound(p, CHAN_WEAPON, "zombie/hit.wav", 1, ATTN_NORM);
	}
	else
		sound(p, CHAN_WEAPON, "weapons/empty.wav", 0.7, ATTN_NORM);
};

void() PlayerPreThink =
{
	local float imp, nb, rise;

	if (self.deadflag != DEAD_NO)
	{
		self.zm_prompt = "";
		return;
	}

	if (self.zm_isbot) bot_think();
	Move_Update(self);

	// regeneracion de vida (como en CoD: a los 5 s sin recibir dano)
	if (self.health < self.max_health && time > self.zm_lasthurt + 5)
	{
		self.health = self.health + frametime * 45;
		if (self.health > self.max_health) self.health = self.max_health;
	}

	if (self.zm_reload_end && time >= self.zm_reload_end)
		W_ReloadDone(self);

	// impulsos: 1-4 elegir arma, 10 siguiente, 20 comprar, 21 recargar
	imp = self.impulse;
	// acciones por botones del cliente (tactil/mando): flanco de subida de cada boton
	nb = 0;
	if (self.button5) nb = nb | 16;
	if (self.button7) nb = nb | 64;
	if (self.button8) nb = nb | 128;
	rise = nb & (255 - self.zm_prevb);
	self.zm_prevb = nb;
	if (rise && !imp)
	{
		if (nb == 144) imp = 23;
		else if (rise & 64) imp = 22;
		else if (rise & 16) imp = 21;
		else if (rise & 128) imp = 10;
	}
	if (imp)
	{
		self.impulse = 0;
		if (imp >= 1 && imp <= 4) W_Select(self, imp - 1);
		else if (imp == 10) W_Next(self);
		else if (imp == 20) Buy_Try(self);
		else if (imp == 21) W_Reload(self);
		else if (imp == 22) Melee(self);
		else if (imp == 23)
		{	// "usar": compra si hay algo cerca; si no, recarga
			if (Buy_Near(self) != world) Buy_Try(self);
			else W_Reload(self);
		}
	}

	// salto (boton tactil o tecla)
	if (self.button2 && (self.flags & FL_ONGROUND) && time > self.zm_nextjump)
	{
		self.flags = self.flags - FL_ONGROUND;
		self.velocity_z = self.velocity_z + 270;
		self.zm_nextjump = time + 0.4;
	}

	// disparo
	W_Load(self.zm_cur);
	if (self.button0)
	{
		if (w_auto || !self.zm_fire_held)
			W_Fire(self);
		self.zm_fire_held = 1;
	}
	else
		self.zm_fire_held = 0;

	// datos para el HUD
	Buy_Prompt(self);
	self.zm_clip = GetClip(self, self.zm_cur);
	self.zm_reserve = GetRes(self, self.zm_cur);
	self.currentammo = self.zm_clip;
};

void() PlayerPostThink =
{
	local float f;

	if (self.deadflag != DEAD_NO) return;

	if (self.zm_flash_end && time > self.zm_flash_end)
	{
		self.effects = self.effects - (self.effects & EF_MUZZLEFLASH);
		self.zm_flash_end = 0;
	}

	if (self.zm_reload_end)
	{
		W_Load(self.zm_cur);
		f = (time - (self.zm_reload_end - w_reload)) / w_reload;
		f = 4 + floor(f * 4);
		if (f > 7) f = 7;
		if (f < 4) f = 4;
		self.weaponframe = f;
	}
	else if (self.zm_wf_end && time > self.zm_wf_end)
	{
		self.weaponframe = 0;
		self.zm_wf_end = 0;
	}
};
