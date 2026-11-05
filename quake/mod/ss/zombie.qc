// ============================================================================
//  Zombies: aparicion, IA (persecucion + ataque), muerte
//  Animacion del modelo: 0-7 caminar, 8-11 atacar, 12-15 morir
// ============================================================================

entity(vector org) zm_nearest_player =
{
	local entity p, best;
	local float d, bd;
	bd = 999999;
	best = world;
	p = find(world, classname, "player");
	while (p)
	{
		if (p.health > 0 && p.deadflag == DEAD_NO)
		{
			d = vlen(p.origin - org);
			if (d < bd)
			{
				bd = d;
				best = p;
			}
		}
		p = find(p, classname, "player");
	}
	return best;
};

void() zombie_dead_think =
{
	local float t, f;
	t = time - self.zm_dead_t;
	if (t > 5)
	{
		remove(self);
		return;
	}
	f = floor(t * 8);
	if (f > 3) f = 3;
	self.frame = 12 + f;
	self.nextthink = time + 0.05;
};

void(entity z, entity attacker, float head) zombie_die =
{
	z.health = 0;
	z.takedamage = DAMAGE_NO;
	z.solid = SOLID_NOT;
	z.zm_attacking = 0;
	z.think = zombie_dead_think;
	z.nextthink = time + 0.05;
	z.zm_dead_t = time;
	z.frame = 12;
	if (attacker.classname == "player")
	{
		if (head)
			attacker.zm_points = attacker.zm_points + 100;
		else
			attacker.zm_points = attacker.zm_points + 60;
		attacker.zm_kills = attacker.zm_kills + 1;
	}
	zm_kills_total = zm_kills_total + 1;
	if (zm_test) dprint(strcat("ZM: kill #", ftos(zm_kills_total), " left=", ftos(zm_left - 1), " alive=", ftos(zm_alive - 1), " t=", ftos(time), "\n"));
	zm_alive = zm_alive - 1;
	zm_left = zm_left - 1;
	sound(z, CHAN_VOICE, "zombie/die.wav", 1, ATTN_NORM);
};

void() zombie_think =
{
	local entity pl;
	local vector d;
	local float dist, f;

	self.nextthink = time + 0.1;
	if (self.health <= 0) return;

	// atrapado en telarana (Widow's Wine): inmovil y blanquecino
	if (self.zm_web_end)
	{
		if (time < self.zm_web_end)
		{
			self.colormod = '2.2 2.2 2.4';
			self.velocity = '0 0 0';
			self.zm_attacking = 0;
			self.frame = 0;
			return;
		}
		self.zm_web_end = 0;
		self.colormod = '0 0 0';
	}

	pl = zm_nearest_player(self.origin);
	if (pl == world)
	{
		self.frame = 0;
		return;
	}
	d = pl.origin - self.origin;
	dist = vlen(d);

	// golpe en curso
	if (self.zm_attacking)
	{
		f = 8 + floor((time - (self.zm_atk_hit - 0.45)) * 8);
		if (f > 11) f = 11;
		self.frame = f;
		if (time >= self.zm_atk_hit)
		{
			self.zm_attacking = 0;
			self.zm_atk_end = time + 0.6;
			if (dist < 80 && fabs(d_z) < 64 && pl.health > 0)
			{
				sound(self, CHAN_WEAPON, "zombie/hit.wav", 1, ATTN_NORM);
				Hurt(pl, self, 45, 0);
			}
		}
		return;
	}
	if (time < self.zm_atk_end)
	{
		self.frame = 0;
		return;
	}

	self.ideal_yaw = vectoyaw(d);
	ChangeYaw();

	// empieza un golpe
	if (dist < 60 && fabs(d_z) < 56)
	{
		self.zm_attacking = 1;
		self.zm_atk_hit = time + 0.45;
		self.frame = 8;
		// al empezar a golpear: gruñido de ataque
		if (random() < 0.6)
			sound(self, CHAN_VOICE, "zombie/zombie1.wav", 1, ATTN_NORM);
		else
			sound(self, CHAN_VOICE, "zombie/groan2.wav", 1, ATTN_NORM);
		return;
	}

	// detector de atasco: si casi no se mueve, prueba un lado al azar
	if (time > self.zm_lastpos_t + 1.5)
	{
		if (vlen(self.origin - self.zm_lastpos) < 20 && dist > 90)
		{
			self.zm_unstick_end = time + 0.9;
			self.ideal_yaw = self.angles_y + 70 + random() * 220;
		}
		self.zm_lastpos = self.origin;
		self.zm_lastpos_t = time;
	}

	if (time < self.zm_unstick_end)
	{
		walkmove(self.ideal_yaw, self.speed * 0.1);
	}
	else
	{
		self.goalentity = pl;
		self.enemy = pl;
		movetogoal(self.speed * 0.1);
	}

	// caminar
	if (self.frame >= 7 || self.frame < 0)
		self.frame = 0;
	else
		self.frame = self.frame + 1;

	// gruñidos al perseguir: no encima del anterior, y mas seguido cuanto mas cerca del jugador
	if (time >= self.zm_next_voice)
	{
		f = random();
		if (dist < 450)
		{
			if (f < 0.55)
				sound(self, CHAN_VOICE, "zombie/zombie1.wav", 1, ATTN_NORM);
			else if (f < 0.75)
				sound(self, CHAN_VOICE, "zombie/groan1.wav", 1, ATTN_NORM);
			else if (f < 0.9)
				sound(self, CHAN_VOICE, "zombie/groan2.wav", 1, ATTN_NORM);
			else
				sound(self, CHAN_VOICE, "zombie/groan3.wav", 1, ATTN_NORM);
		}
		else if (f < 0.5)
			sound(self, CHAN_VOICE, "zombie/groan3.wav", 0.8, ATTN_IDLE);
		else
			sound(self, CHAN_VOICE, "zombie/zombie1.wav", 0.8, ATTN_IDLE);
		// entre 2 y 6 s hasta el siguiente (los lejanos mas espaciados)
		self.zm_next_voice = time + 2 + random() * 3 + ((dist > 450) ? 2 : 0);
	}
};

entity(vector org, float hp, float spd) zombie_spawn =
{
	local entity z, old, near;
	local float ok;

	// hay alguien ocupando el punto?
	near = findradius(org, 44);
	while (near)
	{
		if (near.classname == "zombie" || near.classname == "player")
			return world;
		near = near.chain;
	}

	z = spawn();
	z.classname = "zombie";
	setmodel(z, "models/zombie.md3");
	z.movetype = MOVETYPE_STEP;
	z.solid = SOLID_SLIDEBOX;
	z.flags = FL_MONSTER;
	setsize(z, '-16 -16 -24', '16 16 40');
	z.zm_next_voice = time + 0.5 + random() * 3;
	setorigin(z, org + '0 0 26');

	old = self;
	self = z;
	ok = droptofloor();
	self = old;
	if (!ok)
	{
		remove(z);
		return world;
	}

	z.health = hp;
	z.takedamage = DAMAGE_AIM;
	z.speed = spd;
	z.yaw_speed = 40;
	z.angles_y = random() * 360;
	z.ideal_yaw = z.angles_y;
	z.think = zombie_think;
	z.nextthink = time + 0.1 + random() * 0.2;
	z.zm_lastpos = z.origin;
	z.zm_lastpos_t = time;
	z.frame = floor(random() * 8);
	zm_alive = zm_alive + 1;
	if (zm_test) dprint(strcat("ZM: spawn alive=", ftos(zm_alive), " t=", ftos(time), "\n"));
	return z;
};
