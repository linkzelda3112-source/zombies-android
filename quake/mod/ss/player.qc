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

void() PlayerPreThink =
{
	local float imp;

	if (self.deadflag != DEAD_NO)
	{
		self.zm_prompt = "";
		return;
	}

	if (self.zm_isbot) bot_think();

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
	if (imp)
	{
		self.impulse = 0;
		if (imp >= 1 && imp <= 4) W_Select(self, imp - 1);
		else if (imp == 10) W_Next(self);
		else if (imp == 20) Buy_Try(self);
		else if (imp == 21) W_Reload(self);
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
