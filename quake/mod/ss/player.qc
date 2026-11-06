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

// Widow's Wine: al recibir un golpe cuerpo a cuerpo estalla una telarana que dana al que golpeo
// y atrapa a los zombies cercanos
void(entity p, entity att) Widow_Burst =
{
	local entity z;
	p.zm_widow_next = time + 6;
	z = find(world, classname, "zombie");
	while (z)
	{
		if (z != att && z.health > 0 && vlen(z.origin - p.origin) < 170)
		{
			z.zm_web_end = time + 6;
			z.zm_attacking = 0;
			Web_Cocoon(z, 6);
		}
		z = find(z, classname, "zombie");
	}
	if (att.classname == "zombie" && att.health > 0)
	{
		att.zm_web_end = time + 6;
		att.zm_attacking = 0;
		Web_Cocoon(att, 6);
		Hurt(att, p, 150, FALSE);
	}
	Web_Burst(p.origin + '0 0 20', 170);
	sound(p, CHAN_ITEM, "misc/nobuy.wav", 0.6, ATTN_NORM);
	bprint("ZM: widow's wine web burst\n");
};

void(entity targ, entity attacker, float dmg, float head) Hurt =
{
	if (targ.classname == "zombie")
	{
		if (targ.health <= 0) return;
		if (attacker.classname == "player" && attacker.zm_gum_insta > time) dmg = targ.health + 1;
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
		{
			sound(targ, CHAN_VOICE, "player/pain.wav", 1, ATTN_NORM);
			if ((targ.zm_perks & 8) && time > targ.zm_widow_next && attacker.classname == "zombie")
				Widow_Burst(targ, attacker);
		}
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

	// prueba de granadas: con Widow's Wine lanza una cada vez que puede
	if (time > 12)
	{
		self.zm_perks = self.zm_perks | 8;
		if (self.zm_nades > 0 && !self.zm_nade_state) self.impulse = 24;
	}

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
	self.zm_perks = 0;
	self.zm_nades = 2;
	self.zm_nade_next = 0;
	self.zm_nade_state = 0;
	self.zm_widow_next = 0;
	self.zm_gum_insta = 0;
	self.zm_gum_free = 0;
	self.zm_gum_end = 0;
	self.zm_gum_uses = 0;
	self.zm_gumname = "";
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

// ---- granadas: fragmentacion o Widow's Wine (telarana) -------------------------
// Esfera de telarana que estalla: crece rapido (con rebote suave), gira y se desvanece.
void() Web_Think =
{
	local float t, k;
	t = time - self.zm_t0;
	if (t > self.zm_dur)
	{
		remove(self);
		return;
	}
	k = t / 0.4;
	if (k > 1) k = 1;
	k = 1 - (1 - k) * (1 - k);
	self.scale = 1 + (self.zm_scl - 1) * k;
	if (t < 0.4) self.alpha = 1;
	else self.alpha = 1 - (t - 0.4) / (self.zm_dur - 0.4);
	if (self.alpha < 0.04) self.alpha = 0.04;
	self.angles_y = t * 140;
	self.nextthink = time + 0.05;
};

void(vector org, float scl, float dur, vector tint, float lit) Web_Layer =
{
	local entity e;
	e = spawn();
	e.classname = "web";
	e.movetype = MOVETYPE_NONE;
	e.solid = SOLID_NOT;
	setmodel(e, "models/web.md3");
	setorigin(e, org);
	e.scale = 1;
	e.alpha = 1;
	e.colormod = tint;
	e.effects = EF_ADDITIVE;
	if (lit) e.effects = e.effects | EF_BRIGHTLIGHT;
	e.zm_t0 = time;
	e.zm_scl = scl;
	e.zm_dur = dur;
	e.think = Web_Think;
	e.nextthink = time + 0.05;
};

// estallido: nucleo blanco, esfera violeta que se expande y onda verde mas grande
void(vector org, float rad) Web_Burst =
{
	local float sc;
	sc = rad / 32;
	Web_Layer(org, sc * 0.55, 0.8, '2 2 2', FALSE);
	Web_Layer(org, sc, 2.4, '1.5 0.9 2.2', TRUE);
	Web_Layer(org, sc * 1.25, 1.3, '0.5 1.8 0.8', FALSE);
	te_gunshot(org);
	te_gunshot(org + '0 0 24');
};

// capullo de telarana alrededor de un zombie atrapado
void() Cocoon_Think =
{
	if (!self.owner || self.owner.health <= 0 || time > self.zm_t0)
	{
		remove(self);
		return;
	}
	setorigin(self, self.owner.origin + '0 0 6');
	self.scale = 1.25;
	if (self.zm_t0 - time < 1) self.alpha = (self.zm_t0 - time) * 0.7;
	self.nextthink = time + 0.1;
};

void(entity z, float dur) Web_Cocoon =
{
	local entity e;
	e = spawn();
	e.classname = "cocoon";
	e.owner = z;
	e.movetype = MOVETYPE_NONE;
	e.solid = SOLID_NOT;
	setmodel(e, "models/web.md3");
	setorigin(e, z.origin + '0 0 6');
	e.scale = 1.25;
	e.alpha = 0.7;
	e.colormod = '1.3 1.3 1.6';
	e.effects = EF_ADDITIVE;
	e.zm_t0 = time + dur;
	e.think = Cocoon_Think;
	e.nextthink = time + 0.1;
};

void() Nade_Explode =
{
	local entity z, nz;
	local float d, rad, dmg;
	if (self.zm_nadetype == 2)
	{
		rad = 240;
		Web_Burst(self.origin, rad);
		sound(self, CHAN_WEAPON, "grenade/web.wav", 1, ATTN_NORM);
		bprint("ZM: widow grenade burst\n");
	}
	else
	{
		rad = 170;
		te_explosion(self.origin);
		sound(self, CHAN_WEAPON, "grenade/explode.wav", 1, ATTN_NORM);
		bprint("ZM: frag grenade burst\n");
	}
	z = find(world, classname, "zombie");
	while (z)
	{
		nz = find(z, classname, "zombie");
		d = vlen(z.origin - self.origin);
		if (z.health > 0 && d < rad)
		{
			if (self.zm_nadetype == 2)
			{
				z.zm_web_end = time + 8;
				z.zm_attacking = 0;
				Web_Cocoon(z, 8);
				dmg = 150;
			}
			else
				dmg = 400 * (1 - d / rad) + 40;
			Hurt(z, self.owner, dmg, FALSE);
		}
		z = nz;
	}
	remove(self);
};

void() Nade_Touch =
{
	if (other == self.owner) return;
	if (self.zm_nadetype == 2 && self.movetype != MOVETYPE_NONE)
	{
		// se pega a la superficie (o al zombie) y estalla enseguida
		self.movetype = MOVETYPE_NONE;
		self.velocity = '0 0 0';
		self.avelocity = '0 0 0';
		self.nextthink = time + 0.8;
	}
	else
		sound(self, CHAN_AUTO, "weapons/empty.wav", 0.4, ATTN_NORM);
};

// suelta la granada (a mitad de la animacion de lanzamiento)
void(entity p) Nade_Release =
{
	local entity e;
	p.punchangle = '-9 0 0';
	sound(p, CHAN_ITEM, "grenade/throw.wav", 1, ATTN_NORM);
	makevectors(p.v_angle);
	e = spawn();
	e.classname = "grenade";
	e.owner = p;
	e.movetype = MOVETYPE_BOUNCE;
	e.solid = SOLID_BBOX;
	if (p.zm_perks & 8)
	{
		e.zm_nadetype = 2;
		setmodel(e, "models/grenade_w.md3");
	}
	else
	{
		e.zm_nadetype = 1;
		setmodel(e, "models/grenade.md3");
	}
	setsize(e, '-3 -3 -3', '3 3 3');
	setorigin(e, p.origin + p.view_ofs + v_forward * 14);
	e.velocity = v_forward * 650 + v_up * 190 + p.velocity * 0.3;
	e.avelocity = '420 0 260';
	e.touch = Nade_Touch;
	e.think = Nade_Explode;
	e.nextthink = time + 2.2;
};

// empieza el lanzamiento: sale la granada en la mano, se quita el seguro y se lanza
void(entity p) Nade_Throw =
{
	if (p.zm_nades <= 0 || time < p.zm_nade_next) return;
	if (p.zm_nade_state) return;
	if (p.zm_reload_end)
	{
		p.zm_reload_end = 0;      // lanzar cancela la recarga (como en BO3)
		p.zm_reloading = 0;
	}
	p.zm_nades = p.zm_nades - 1;
	p.zm_nade_next = time + 1.3;
	p.zm_nade_state = 1;
	p.zm_nade_t0 = time;
	p.zm_nextshot = time + 1.1;
	p.zm_flash_end = 0;
	if (p.zm_perks & 8) p.weaponmodel = "models/v_grenade_w.md3";
	else p.weaponmodel = "models/v_grenade.md3";
	p.weaponframe = 0;
	sound(p, CHAN_ITEM, "weapons/empty.wav", 0.5, ATTN_NORM);
};

// animacion en primera persona (10 cuadros de 0.105 s): 0-3 seguro, 4-5 impulso, 6-9 lanzamiento y retorno
void(entity p) Nade_Anim =
{
	local float t, f;
	t = time - p.zm_nade_t0;
	if (p.zm_nade_state == 1 && t >= 0.27)
	{
		sound(p, CHAN_ITEM, "weapons/empty.wav", 0.8, ATTN_NORM);       // se quita el seguro
		p.zm_nade_state = 2;
	}
	if (p.zm_nade_state == 2 && t >= 0.6)
	{
		Nade_Release(p);
		p.zm_nade_state = 3;
	}
	if (t >= 1.06)
	{
		p.zm_nade_state = 0;
		W_Equip(p);
		return;
	}
	f = floor(t / 0.105);
	if (f > 9) f = 9;
	p.weaponframe = f;
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
	self.zm_gumleft = self.zm_gum_end - time;
	if (self.zm_gumleft < 0) self.zm_gumleft = 0;
	if (self.zm_gumleft <= 0) self.zm_gumname = "";

	// regeneracion de vida (como en CoD: a los 5 s sin recibir dano)
	if (self.health < self.max_health && time > self.zm_lasthurt + 5)
	{
		self.health = self.health + frametime * 45;
		if (self.health > self.max_health) self.health = self.max_health;
	}

	if (self.zm_reload_end && time >= self.zm_reload_end)
		W_ReloadDone(self);
	if (self.zm_nade_state)
		Nade_Anim(self);

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
		else if (nb == 192) imp = 24;
		else if (rise & 64) imp = 22;
		else if (rise & 16) imp = 21;
		else if (rise & 128) imp = 10;
	}
	if (imp)
	{
		self.impulse = 0;
		if (imp >= 1 && imp <= 5) W_Select(self, imp - 1);
		else if (imp == 10) W_Next(self);
		else if (imp == 20) Buy_Try(self);
		else if (imp == 24) Nade_Throw(self);
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

	if (self.zm_nade_state)
		Nade_Anim(self);
	else if (self.zm_reload_end)
	{
		W_Load(self.zm_cur);
		f = (time - (self.zm_reload_end - W_ReloadTime(self))) / W_ReloadTime(self);
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
