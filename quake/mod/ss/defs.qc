// ============================================================================
//  Zombies (Quake / FTE) - definiciones del servidor
// ============================================================================

#ifndef TRUE
#define TRUE 1
#define FALSE 0
#endif

// ---- estado de vida (deadflag) ---------------------------------------------
#define DEAD_NO    0
#define DEAD_DYING 1
#define DEAD_DEAD  2

// ---- armas -----------------------------------------------------------------
#define W_PISTOL  0
#define W_SMG     1
#define W_SHOTGUN 2
#define W_RIFLE   3
#define W_COUNT   4

// ---- estados de la partida --------------------------------------------------
#define ZS_WAIT   0   // esperando jugador
#define ZS_INTER  1   // pausa entre rondas
#define ZS_ACTIVE 2   // ronda en curso
#define ZS_OVER   3   // todos muertos

// ---- globales (algunas se mandan al HUD con globalstat) ---------------------
float zm_round;        // ronda actual
float zm_left;         // zombies que faltan por matar en la ronda
float zm_state;        // ZS_*
float zm_gameover;     // 1 cuando se acabó la partida
float zm_alive;        // zombies vivos ahora mismo
float zm_to_spawn;     // zombies de la ronda que aún no han salido
float zm_state_end;    // cuando termina el estado actual
float zm_next_spawn;   // cuando sale el siguiente zombie
float zm_hp;           // vida de los zombies de esta ronda
float zm_speed;        // velocidad base de esta ronda
float zm_test;         // 0 normal, 1 bot quieto, 2 bot que dispara y es inmortal
float zm_kills_total;
float zm_botspawned;

// ---- campos por jugador ----------------------------------------------------
.float zm_points;
.float zm_kills;
.float zm_lasthurt;
.float zm_cur;          // arma actual
.float zm_own;          // armas que tiene (bit por arma)
.float zm_clip0, zm_clip1, zm_clip2, zm_clip3;
.float zm_res0, zm_res1, zm_res2, zm_res3;
.float zm_reload_end;   // cuando termina de recargar (0 = no recarga)
.float zm_nextshot;
.float zm_wf_end;       // cuando vuelve la animacion del arma a reposo
.float zm_flash_end;    // cuando se apaga el fogonazo
.float zm_isbot;
.float zm_fire_held;    // el gatillo seguia pulsado el frame anterior
// espejo para el HUD
.float zm_clip;
.float zm_reserve;
.float zm_hit;          // contador de impactos (para el marcador)
.float zm_hurt;         // contador de golpes recibidos (para el flash rojo)
.float zm_reloading;
.float zm_nextjump;
.float zm_next_voice;
.float zm_prevb;
.float zm_stance;      // 0 de pie, 1 agachado, 2 deslizando
.float zm_slide_end;
.float zm_slide_start;
.vector zm_slidedir;
.float zm_sprinting;
.float zm_perks;       // bits: 1 jugger-nog, 2 double tap, 4 speed cola, 8 widow's wine
.float zm_widow_next;  // cuando puede volver a activarse Widow's Wine
.float zm_web_end;     // (zombie) hasta cuando esta atrapado en telarana
.float zm_gum_insta;   // hasta cuando dura Kill Joy (muerte instantanea)
.float zm_gum_free;    // hasta cuando dura Free Fire (municion infinita)
.float zm_gum_end;     // hasta cuando se muestra el chicle en el HUD
.float zm_gum_uses;    // chicles comprados
.float zm_gumleft;     // segundos restantes (espejo para el HUD)
.string zm_gumname;    // nombre del chicle (espejo para el HUD)
.float zm_nextmelee;
.float zm_b4;
.string zm_prompt;

// ---- campos por zombie -----------------------------------------------------
.float speed;           // velocidad de carrera (unidades/segundo)
.float zm_atk_end;
.float zm_atk_hit;
.float zm_attacking;
.float zm_walk_t;
.vector zm_lastpos;
.float zm_lastpos_t;
.float zm_unstick_end;
.float zm_dead_t;

// ---- clave del mapa para las compras en pared ------------------------------
.float wep;

// ---- utilidades ------------------------------------------------------------
float() crandom =
{
	return 2 * (random() - 0.5);
};

void() SUB_Remove =
{
	remove(self);
};

// ---- tabla de armas (se carga con W_Load) -----------------------------------
float w_dmg, w_clip, w_resmax, w_pellets, w_auto, w_cost, w_ammocost;
float w_rate, w_reload, w_spread, w_hip;
string w_name, w_vmodel, w_snd;

void(float w) W_Load =
{
	if (w == W_SMG)
	{
		w_name = "KUDA SMG";     w_vmodel = "models/v_smg.md3";     w_snd = "weapons/smg.wav";
		w_dmg = 22;  w_clip = 30; w_resmax = 150; w_pellets = 1; w_auto = TRUE;
		w_rate = 0.085; w_reload = 2.1; w_spread = 0.035; w_hip = 0.05; w_cost = 1000; w_ammocost = 500;
	}
	else if (w == W_SHOTGUN)
	{
		w_name = "TRENCH GUN";   w_vmodel = "models/v_shotgun.md3"; w_snd = "weapons/shotgun.wav";
		w_dmg = 16;  w_clip = 6;  w_resmax = 36;  w_pellets = 8; w_auto = FALSE;
		w_rate = 0.85;  w_reload = 2.8; w_spread = 0.085; w_hip = 0.035; w_cost = 1500; w_ammocost = 750;
	}
	else if (w == W_RIFLE)
	{
		w_name = "G-43 RIFLE";   w_vmodel = "models/v_rifle.md3";   w_snd = "weapons/rifle.wav";
		w_dmg = 95;  w_clip = 10; w_resmax = 60;  w_pellets = 1; w_auto = FALSE;
		w_rate = 0.5;   w_reload = 2.3; w_spread = 0.004; w_hip = 0.055; w_cost = 2000; w_ammocost = 1000;
	}
	else
	{
		w_name = "M1911";        w_vmodel = "models/v_pistol.md3";  w_snd = "weapons/pistol.wav";
		w_dmg = 30;  w_clip = 8;  w_resmax = 40;  w_pellets = 1; w_auto = FALSE;
		w_rate = 0.25;  w_reload = 1.6; w_spread = 0.006; w_hip = 0.03; w_cost = 0; w_ammocost = 500;
	}
};

float(entity e, float w) GetClip =
{
	if (w == 0) return e.zm_clip0;
	if (w == 1) return e.zm_clip1;
	if (w == 2) return e.zm_clip2;
	return e.zm_clip3;
};

void(entity e, float w, float v) SetClip =
{
	if (w == 0) e.zm_clip0 = v;
	else if (w == 1) e.zm_clip1 = v;
	else if (w == 2) e.zm_clip2 = v;
	else e.zm_clip3 = v;
};

float(entity e, float w) GetRes =
{
	if (w == 0) return e.zm_res0;
	if (w == 1) return e.zm_res1;
	if (w == 2) return e.zm_res2;
	return e.zm_res3;
};

void(entity e, float w, float v) SetRes =
{
	if (w == 0) e.zm_res0 = v;
	else if (w == 1) e.zm_res1 = v;
	else if (w == 2) e.zm_res2 = v;
	else e.zm_res3 = v;
};

// ---- prototipos adelantados -------------------------------------------------
void(entity targ, entity attacker, float dmg, float head) Hurt;
void() zombie_think;
entity(vector org, float hp, float spd) zombie_spawn;
