// ============================================================================
//  Mundo: precarga, entidades del mapa y director de rondas
// ============================================================================

// ---- entidades del mapa ----------------------------------------------------
void() info_player_start =
{
};

void() info_zombie_spawn =
{
	self.classname = "info_zombie_spawn";
};

void() zm_buy =
{
	self.classname = "zm_buy";
};

// las luces solo las usa el compilador de mapas
void() light =
{
	remove(self);
};

void() light_fluoro =
{
	remove(self);
};

// paredes decorativas (placas de compra, etc.)
void() func_wall =
{
	self.angles = '0 0 0';
	self.movetype = MOVETYPE_PUSH;
	self.solid = SOLID_BSP;
	setmodel(self, self.model);
};

void() main =
{
};

void() worldspawn =
{
	zm_test = cvar("zm_test");

	precache_model("models/zombie.md3");
	precache_model("models/grenade.md3");
	precache_model("models/grenade_w.md3");
	precache_model("models/web.md3");
	precache_model("models/v_haymaker.md3");
	precache_model("models/v_grenade.md3");
	precache_model("models/v_grenade_w.md3");
	precache_sound("grenade/throw.wav");
	precache_sound("grenade/explode.wav");
	precache_sound("grenade/web.wav");
	precache_model("models/v_pistol.md3");
	precache_model("models/v_smg.md3");
	precache_model("models/v_shotgun.md3");
	precache_model("models/v_rifle.md3");

	precache_sound("weapons/pistol.wav");
	precache_sound("weapons/smg.wav");
	precache_sound("weapons/shotgun.wav");
	precache_sound("weapons/rifle.wav");
	precache_sound("weapons/reload.wav");
	precache_sound("weapons/empty.wav");
	precache_sound("zombie/zombie1.wav");
	precache_sound("zombie/groan1.wav");
	precache_sound("zombie/groan2.wav");
	precache_sound("zombie/groan3.wav");
	precache_sound("zombie/hit.wav");
	precache_sound("zombie/pain.wav");
	precache_sound("zombie/die.wav");
	precache_sound("player/pain.wav");
	precache_sound("player/death.wav");
	precache_sound("misc/buy.wav");
	precache_sound("misc/nobuy.wav");
	precache_sound("misc/round_start.wav");
	precache_sound("misc/round_end.wav");
	precache_sound("misc/gameover.wav");

	lightstyle(0, "m");

	// valores que viajan al HUD (CSQC)
	clientstat(STAT_USER + 0, EV_FLOAT, zm_points);
	clientstat(STAT_USER + 1, EV_FLOAT, zm_clip);
	clientstat(STAT_USER + 2, EV_FLOAT, zm_reserve);
	clientstat(STAT_USER + 3, EV_FLOAT, zm_cur);
	clientstat(STAT_USER + 4, EV_FLOAT, zm_hit);
	clientstat(STAT_USER + 5, EV_FLOAT, zm_hurt);
	clientstat(STAT_USER + 6, EV_STRING, zm_prompt);
	clientstat(STAT_USER + 7, EV_FLOAT, zm_kills);
	clientstat(STAT_USER + 8, EV_FLOAT, zm_reloading);
	clientstat(STAT_USER + 9, EV_FLOAT, max_health);
	clientstat(STAT_USER + 17, EV_FLOAT, zm_nades);
	clientstat(STAT_USER + 16, EV_FLOAT, zm_perks);
	clientstat(STAT_USER + 14, EV_STRING, zm_gumname);
	clientstat(STAT_USER + 15, EV_FLOAT, zm_gumleft);
	globalstat(STAT_USER + 10, EV_FLOAT, "zm_round");
	globalstat(STAT_USER + 11, EV_FLOAT, "zm_left");
	globalstat(STAT_USER + 12, EV_FLOAT, "zm_state");
	globalstat(STAT_USER + 13, EV_FLOAT, "zm_gameover");

	zm_state = ZS_WAIT;
	zm_round = 0;
	zm_gameover = 0;
	zm_botspawned = 0;
};

// ---- director de rondas ----------------------------------------------------
entity() zm_pick_spawn =
{
	local entity s, near;
	local float n, pick, i, tries;

	n = 0;
	s = find(world, classname, "info_zombie_spawn");
	while (s)
	{
		n = n + 1;
		s = find(s, classname, "info_zombie_spawn");
	}
	if (n == 0) return world;

	for (tries = 0; tries < 6; tries = tries + 1)
	{
		pick = floor(random() * n);
		i = 0;
		s = find(world, classname, "info_zombie_spawn");
		while (s)
		{
			if (i == pick) break;
			i = i + 1;
			s = find(s, classname, "info_zombie_spawn");
		}
		near = zm_nearest_player(s.origin);
		// preferir puntos lejos del jugador
		if (near == world || vlen(near.origin - s.origin) > 350) return s;
	}
	return s;
};

void() zm_start_round =
{
	local float i, total;
	local entity pp;

	zm_round = zm_round + 1;
	total = floor(6 + zm_round * 3.5);
	zm_to_spawn = total;
	zm_left = total;

	if (zm_round < 10)
		zm_hp = 50 + zm_round * 100;      // como BO3: 150, 250, 350 ... 950
	else
	{
		zm_hp = 950;
		for (i = 9; i < zm_round; i = i + 1)
			zm_hp = zm_hp * 1.1;
	}
	if (zm_hp > 5000) zm_hp = 5000;

	if (zm_round <= 2) zm_speed = 55;
	else if (zm_round <= 4) zm_speed = 90;
	else if (zm_round <= 7) zm_speed = 130;
	else zm_speed = 165;

	// las granadas se recuperan al empezar la ronda (Widow's Wine: 4, normales: 2)
	pp = find(world, classname, "player");
	while (pp)
	{
		if (pp.zm_perks & 8) pp.zm_nades = 4;
		else if (pp.zm_nades < 2) pp.zm_nades = 2;
		pp = find(pp, classname, "player");
	}

	zm_state = ZS_ACTIVE;
	zm_next_spawn = time + 1;
	bprint(strcat("ZM: [t=", ftos(rint(time)), "] round ", ftos(zm_round), " start, zombies=", ftos(total), " hp=", ftos(zm_hp), "\n"));
	sound(world, CHAN_AUTO, "misc/round_start.wav", 1, ATTN_NONE);
};

void() StartFrame =
{
	local entity p, b, old, sp, z;
	local float players, alive, gap;

	// jugador de prueba (solo con zm_test)
	if (zm_test && !zm_botspawned && time > 1.5)
	{
		zm_botspawned = 1;
		b = find(world, classname, "player");
		if (b != world) b = world;      // ya hay alguien (el bot de la partida anterior)
		else b = spawnclient();
		if (b != world)
		{
			old = self;
			self = b;
			self.netname = "TESTBOT";
			self.zm_isbot = 1;
			SetNewParms();
			ClientConnect();
			PutClientInServer();
			self = old;
		}
	}

	players = 0;
	alive = 0;
	p = find(world, classname, "player");
	while (p)
	{
		players = players + 1;
		if (p.deadflag == DEAD_NO) alive = alive + 1;
		p = find(p, classname, "player");
	}

	if (zm_state == ZS_WAIT)
	{
		if (players > 0)
		{
			zm_state = ZS_INTER;
			zm_state_end = time + 5;
			if (zm_test) zm_state_end = time + 1;
			bprint("ZM: game start\n");
		}
		return;
	}

	if (players > 0 && alive == 0 && zm_state != ZS_OVER)
	{
		zm_state = ZS_OVER;
		zm_gameover = 1;
		zm_state_end = time + 7;
		sound(world, CHAN_AUTO, "misc/gameover.wav", 1, ATTN_NONE);
		bprint(strcat("ZM: game over, round ", ftos(zm_round), ", kills ", ftos(zm_kills_total), "\n"));
		return;
	}

	if (zm_state == ZS_OVER)
	{
		if (time > zm_state_end)
		{
			zm_state_end = time + 9999;
			localcmd("map zombies\n");
		}
		return;
	}

	if (zm_state == ZS_INTER)
	{
		if (time > zm_state_end) zm_start_round();
		return;
	}

	// ZS_ACTIVE: sacar zombies poco a poco
	if (zm_to_spawn > 0 && zm_alive < 18 && time > zm_next_spawn)
	{
		z = world;
		sp = zm_pick_spawn();
		if (sp != world)
		{
			z = zombie_spawn(sp.origin, zm_hp, zm_speed * (0.85 + random() * 0.3));
			if (z != world) zm_to_spawn = zm_to_spawn - 1;
		}
		gap = 1.8 - zm_round * 0.1;
		if (gap < 0.6) gap = 0.6;
		if (zm_test) gap = 0.4;
		zm_next_spawn = time + gap;
		if (z == world) zm_next_spawn = time + 0.25;
	}

	if (zm_left <= 0 && zm_to_spawn <= 0)
	{
		zm_state = ZS_INTER;
		zm_state_end = time + 8;
		if (zm_test) zm_state_end = time + 2;
		sound(world, CHAN_AUTO, "misc/round_end.wav", 1, ATTN_NONE);
		bprint(strcat("ZM: [t=", ftos(rint(time)), "] round ", ftos(zm_round), " complete, kills=", ftos(zm_kills_total), "\n"));
	}
};
