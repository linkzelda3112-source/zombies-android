// ============================================================================
//  Armas: disparo, recarga, compra en pared
// ============================================================================

float(float w) WBit =
{
	if (w == 0) return 1;
	if (w == 1) return 2;
	if (w == 2) return 4;
	return 8;
};

void(entity p) W_Equip =
{
	W_Load(p.zm_cur);
	p.weaponmodel = w_vmodel;
	p.weaponframe = 0;
	p.zm_reload_end = 0;
	p.zm_reloading = 0;
};

void(entity p, float w) W_Select =
{
	if (w < 0 || w >= W_COUNT) return;
	if (!(p.zm_own & WBit(w))) return;
	if (p.zm_cur == w) return;
	p.zm_cur = w;
	W_Equip(p);
	sound(p, CHAN_ITEM, "weapons/empty.wav", 0.6, ATTN_NORM);
};

void(entity p) W_Next =
{
	local float i, w;
	w = p.zm_cur;
	for (i = 0; i < W_COUNT; i = i + 1)
	{
		w = w + 1;
		if (w >= W_COUNT) w = 0;
		if (p.zm_own & WBit(w))
		{
			W_Select(p, w);
			return;
		}
	}
};

void(entity p) W_Reload =
{
	local float w;
	w = p.zm_cur;
	W_Load(w);
	if (p.zm_reload_end) return;
	if (GetClip(p, w) >= w_clip) return;
	if (GetRes(p, w) <= 0) return;
	p.zm_reload_end = time + w_reload;
	p.zm_reloading = 1;
	p.weaponframe = 4;
	sound(p, CHAN_ITEM, "weapons/reload.wav", 1, ATTN_NORM);
};

void(entity p) W_ReloadDone =
{
	local float w, need, take;
	w = p.zm_cur;
	W_Load(w);
	need = w_clip - GetClip(p, w);
	take = GetRes(p, w);
	if (take > need) take = need;
	SetClip(p, w, GetClip(p, w) + take);
	SetRes(p, w, GetRes(p, w) - take);
	p.zm_reload_end = 0;
	p.zm_reloading = 0;
	p.weaponframe = 0;
};

// resultado de un disparo (traceline ya hecha)
void(entity p) W_TraceHit =
{
	local entity t;
	local float head;
	t = trace_ent;
	if (t != world && t.classname == "zombie" && t.takedamage)
	{
		head = FALSE;
		if ((trace_endpos_z - t.origin_z) > 22) head = TRUE;
		te_blood(trace_endpos, '0 0 0', 30);
		Hurt(t, p, w_dmg, head);
	}
	else if (trace_fraction < 1)
	{
		te_gunshot(trace_endpos);
	}
};

void(entity p) W_Fire =
{
	local float w, clip, i, sp, spd;
	local vector src, dir;
	if (p.zm_sprinting) return;   // no se dispara corriendo
	w = p.zm_cur;
	W_Load(w);
	if (time < p.zm_nextshot) return;
	if (p.zm_reload_end) return;
	clip = GetClip(p, w);
	if (clip <= 0)
	{
		if (GetRes(p, w) > 0)
			W_Reload(p);
		else
		{
			sound(p, CHAN_WEAPON, "weapons/empty.wav", 1, ATTN_NORM);
			p.zm_nextshot = time + 0.4;
		}
		return;
	}
	SetClip(p, w, clip - 1);
	p.zm_nextshot = time + w_rate;
	sound(p, CHAN_WEAPON, w_snd, 1, ATTN_NORM);
	p.weaponframe = 1;
	p.zm_wf_end = time + 0.09;
	p.effects = p.effects | EF_MUZZLEFLASH;
	p.zm_flash_end = time + 0.07;
	if (w == W_SHOTGUN)
		p.punchangle = '-5 0 0';
	else if (w == W_RIFLE)
		p.punchangle = '-4 0 0';
	else
		p.punchangle = '-1.5 0 0';

	makevectors(p.v_angle);
	src = p.origin + p.view_ofs;
	for (i = 0; i < w_pellets; i = i + 1)
	{
		// sin apuntar: mucha mas dispersion (de cadera); apuntando: precision casi total
		if (p.button6) sp = w_spread * 0.3;
		else sp = w_spread + w_hip;
		spd = vlen([p.velocity_x, p.velocity_y, 0]);
		if (spd > 60) sp = sp * (1 + spd / 280 * 0.7);   // moverse abre la dispersion
		if (p.zm_stance) sp = sp * 0.7;
		dir = v_forward + v_right * (crandom() * sp) + v_up * (crandom() * sp);
		dir = normalize(dir);
		traceline(src, src + dir * 4096, FALSE, p);
		W_TraceHit(p);
	}
};

// ---- compras en pared ------------------------------------------------------
entity(entity p) Buy_Near =
{
	local entity b, best;
	local float d, bd;
	bd = 85;
	best = world;
	b = find(world, classname, "zm_buy");
	while (b)
	{
		d = vlen(b.origin - p.origin);
		if (d < bd)
		{
			bd = d;
			best = b;
		}
		b = find(b, classname, "zm_buy");
	}
	return best;
};

void(entity p) Buy_Prompt =
{
	local entity b;
	local float w;
	b = Buy_Near(p);
	if (b == world)
	{
		p.zm_prompt = "";
		return;
	}
	w = b.wep;
	if (w == 10)
	{
		if (p.max_health > 100) p.zm_prompt = "";
		else p.zm_prompt = "BUY JUGGER-NOG  [2500]";
		return;
	}
	W_Load(w);
	if (p.zm_own & WBit(w))
		p.zm_prompt = strcat("BUY AMMO: ", w_name, "  [", ftos(w_ammocost), "]");
	else
		p.zm_prompt = strcat("BUY ", w_name, "  [", ftos(w_cost), "]");
};

void(entity p) Buy_Try =
{
	local entity b;
	local float w, cost;
	b = Buy_Near(p);
	if (b == world) return;
	w = b.wep;
	if (w == 10)
	{
		// perk: vida maxima 250 (se pierde al morir)
		if (p.max_health > 100) return;
		if (p.zm_points < 2500)
		{
			sound(p, CHAN_ITEM, "misc/nobuy.wav", 1, ATTN_NORM);
			return;
		}
		p.zm_points = p.zm_points - 2500;
		p.max_health = 250;
		p.health = 250;
		sound(p, CHAN_ITEM, "misc/buy.wav", 1, ATTN_NORM);
		bprint("ZM: bought perk jugger-nog\n");
		return;
	}
	W_Load(w);
	if (p.zm_own & WBit(w))
	{
		cost = w_ammocost;
		if (GetRes(p, w) >= w_resmax && GetClip(p, w) >= w_clip) return;
		if (p.zm_points < cost)
		{
			sound(p, CHAN_ITEM, "misc/nobuy.wav", 1, ATTN_NORM);
			return;
		}
		p.zm_points = p.zm_points - cost;
		SetRes(p, w, w_resmax);
		SetClip(p, w, w_clip);
		sound(p, CHAN_ITEM, "misc/buy.wav", 1, ATTN_NORM);
		bprint(strcat("ZM: bought ammo ", w_name, "\n"));
	}
	else
	{
		cost = w_cost;
		if (p.zm_points < cost)
		{
			sound(p, CHAN_ITEM, "misc/nobuy.wav", 1, ATTN_NORM);
			return;
		}
		p.zm_points = p.zm_points - cost;
		p.zm_own = p.zm_own | WBit(w);
		SetClip(p, w, w_clip);
		SetRes(p, w, w_resmax);
		p.zm_cur = w;
		W_Equip(p);
		sound(p, CHAN_ITEM, "misc/buy.wav", 1, ATTN_NORM);
		bprint(strcat("ZM: bought weapon ", w_name, "\n"));
	}
};
