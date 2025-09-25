from utilities.vision import MultiVision, Vision

# TODO:

# General images
run_game = MultiVision(
    "run_game.png",
    "run_game_2.png",
    image_name="Run game",
)
password = Vision("password.png")
sync_code = Vision("sync_code.png")
server_cancel = MultiVision(
    "server_cancel.png",
    image_name="server_cancel",
)
connection_confrm_expired = Vision("connection_confirmation_expired.png")
diamond = Vision("diamond.png")
again = Vision("again.png")
lock = Vision("lock.png")
resume = Vision("resume.png")
restore_stamina = Vision(
    "stamuse.png",
    image_name="restore stamina",
)
startbutton = Vision("start.png")
skip = MultiVision(
    "skip.png",
    "demonic_beasts\\skip_masked.png",
    image_name="Skip",
)
dmg = Vision("dmg.png")
reconnect = Vision("reconnect.png")
restart = Vision("restart.png")
result = Vision("result.png")
mission = Vision("mission.png")
reset = Vision("daily_reset.jpg")
random = Vision("random.png")
main_menu_original = Vision("main_menu.png")
main_menu = Vision("main_menu_transparent.png")
main_menu_exclamation = Vision("main_menu_exclamation.png")
register_all = Vision("register_all.png")
apply = Vision("apply.png")
salvage = Vision("salvage.png")
back = Vision("back.png")
equipment = Vision("equipment.png")
onslaught = Vision("onslaught.png")
free_stage = Vision("free_stage.png")
auto_repeat_on = Vision("auto_repeat_on.png")
auto_repeat_off = Vision("auto_repeat_off.png")
tavern = Vision("tavern.png")
fs_dungeon = Vision("fs_dungeon.png")
# equipment_full = Vision("equipment_full.png")
loading_screen = Vision("loading.png")  # Not used
high_grade_equipment = Vision("high_grade_equipment.png")
empty_equipment = Vision("empty_equipment.png")
empty_salvage = Vision("empty_salvage.png")
empty_card_slot = Vision("empty_card_slot.png")
empty_card_slot_2 = Vision("empty_card_slot_2.png")
world = Vision("world.png")
bronze_card = Vision("bronze_card.png")
silver_card = Vision("silver_card.png")
gold_card = Vision("gold_card.png")
auto_off = Vision("autooff.png")
pause = Vision("pause.png")
forfeit = Vision("forfeit.png")
tavern_loading_screen = Vision("tavern_loading_screen.png")
card_slot = Vision("card_slot.png")
close = Vision("close.png")
knighthood = Vision("knighthood.png")
check_in = Vision("check_in.png")
check_in_reward = Vision("check_in_reward.png")
check_in_complete = Vision("check_in_complete.png")
battle_menu = Vision("battle_menu.jpg")
cancel = Vision("cancel.png")
skill_locked = Vision("skill_locked.png")
victory = Vision("victory.png")
global_server = Vision("global_server.png")
yes = Vision("yes.png")
start_quest = Vision("start_quest.png")
essette_shop = Vision("essette_shop.png")
duplicate_connection = MultiVision(
    "duplicate_connection.png",
    "simultaneous_logins.png",
    image_name="duplicate_connection",
)
cross = Vision("cross.png")
pause_fight = Vision("pause_fight.png")
episode_clear = Vision("episode_clear.png")
continue_fight = Vision("continue.png")
annoying_chat_popup = Vision("annoying_chat_popup.png")
change_stats = MultiVision(
    "change_again.png",
    "change_stats.png",
    image_name="Change stats",
)


# SA coin farmer
clock_tower = Vision("sa_coin_dungeon\\clock_tower.png")
clock_tower_floor = Vision("sa_coin_dungeon\\clock_tower_floor.png")
sa_coin = Vision("sa_coin.png")
sa_boss = Vision("sa_coin_dungeon\\sa_boss.png")
chest = Vision("sa_coin_dungeon\\chest.png")
fs_loading_screen = Vision("fs_loading_screen.png")
fs_dungeon_lock = Vision("sa_coin_dungeon\\fs_dungeon_lock.png")
finished_auto_repeat_fight = Vision("finished_auto_repeat_fight.png")


# Equipment farming
auto_repeat_ended = Vision("equipment\\auto_repeat_ended.png")
salvaging_results = Vision("equipment\\salvaging_results.png")
new_tasks_unlocked = Vision("equipment\\new_tasks_unlocked.png")

# Demonic beasts
floor1 = Vision("demonic_beasts\\floor1.png")
floor2 = Vision("demonic_beasts\\floor2.png")
floor3 = Vision("demonic_beasts\\floor3.png")
phase_1 = Vision("demonic_beasts\\phase_1.png")
phase_2 = Vision("demonic_beasts\\phase_2.png")
phase_3 = Vision("demonic_beasts\\phase_3.png")
phase_3_dogs = Vision("dogs\\phase_3_dogs.png")
phase_4 = Vision("demonic_beasts\\phase_4.png")
dead_unit = Vision("demonic_beasts\\dead_unit.png")
db_victory = Vision("demonic_beasts\\db_victory.png")
demonic_beast_battle = Vision("demonic_beasts\\demonic_beast_battle.png")

# For Bird farming
demonic_beast = Vision("demonic_beasts\\creature_nest.png")
hraesvelgr = Vision("demonic_beasts\\hraesvelgr.png")
empty_party = Vision("demonic_beasts\\empty_party.png")
save_party = Vision("demonic_beasts\\save_party.png")
hraesvelgr_screen = Vision("demonic_beasts\\hraesvelgr_screen.png")
skip_bird = Vision("demonic_beasts\\skip_masked.png")
db_loading_screen = Vision("demonic_beasts\\loading_screen.png")
reset_demonic_beast = Vision("demonic_beasts\\reset_demonic_beast.png")
my_turn = Vision("demonic_beasts\\my_turn.png")
floor_3_cleared_db = MultiVision(
    # Bird floor 3 cleared images
    "demonic_beasts\\floor_3_cleared_bird.png",
    "demonic_beasts\\floor_3_cleared_2_bird.png",
    # Deer floor 3 cleared images
    "demonic_beasts\\floor_3_cleared_deer.png",
    "demonic_beasts\\floor_3_cleared_2_deer.png",
    image_name="floor_3_cleared_db",
)
available_floor = Vision("demonic_beasts\\available_floor.png")
creature_destroyed = Vision("demonic_beasts\\creature_destroyed.png")
defeat = Vision("demonic_beasts\\defeat.png")
three_empty_slots = Vision("demonic_beasts\\three_slots.png")
two_empty_slots = Vision("demonic_beasts\\two_slots.png")
weekly_mission = Vision("demonic_beasts\\lazy_weekly_mission.png")
skollandhati = Vision("demonic_beasts\\skollandhati.png")
guaranteed_reward = Vision("demonic_beasts\\guaranteed_reward.png")
meli_aoe = Vision("demonic_beasts\\meli_aoe.png")
meli_ult = Vision("demonic_beasts\\meli_ult.png")
meli_ampli = Vision("demonic_beasts\\meli_ampli.png")
block_skill_debuf = Vision("demonic_beasts\\block_skill_debuff.png")
evasion = Vision("demonic_beasts\\evasion.png")
stance_active = Vision("demonic_beasts\\stance_active.png")
immortality_buff = Vision("demonic_beasts\\immortality.png")
thor_thunderstorm = Vision("demonic_beasts\\thor_thunderstorm.png")
first_reward = Vision("demonic_beasts\\first_reward.png")

# For Deer
eikthyrnir = Vision("deer\\Eikthyrnir.png")
red_buff = MultiVision(
    "deer\\red_buff.png",
    "deer\\red_buff_tiny.png",
    image_name="red_buff",
)
blue_buff = MultiVision(
    "deer\\blue_buff.png",
    "deer\\blue_buff_tiny.png",
    image_name="blue_buff",
)
green_buff = MultiVision(
    "deer\\green_buff.png",
    "deer\\green_buff_tiny.png",
    image_name="green_buff",
)
lv_st = Vision("deer\\lv_st.png")
lv_aoe = Vision("deer\\lv_aoe.png")
lv_ult = Vision("deer\\lv_ult.png")
jorm_1 = Vision("deer\\jorm_1.png")
jorm_2 = Vision("deer\\jorm_2.png")
jorm_ult = Vision("deer\\jorm_ult.png")
roxy_st = Vision("deer\\roxy_st.png")
roxy_aoe = Vision("deer\\roxy_aoe.png")
roxy_ult = Vision("deer\\roxy_ult.png")
escanor_st = Vision("deer\\escanor_st.png")
escanor_aoe = Vision("deer\\escanor_aoe.png")
escanor_ult = Vision("deer\\escanor_ult.png")
# Whale Deer strat additions
albedo_1 = Vision("deer\\albedo_1.png")
albedo_taunt = Vision("deer\\albedo_taunt.png")
albedo_ult = Vision("deer\\albedo_ult.png")
lolimerl_st = Vision("deer\\lolimerl_st.png")
lolimerl_aoe = Vision("deer\\lolimerl_aoe.png")
lolimerl_ult = Vision("deer\\lolimerl_ult.png")
# For the new Deer F4 team
thor_1 = Vision("deer\\thor_1.png")
thor_2 = Vision("demonic_beasts\\thor_thunderstorm.png")
thor_ult = Vision("deer\\thor_ult.png")
freyr_1 = Vision("deer\\freyr_1.png")
freyr_2 = Vision("deer\\freyr_2.png")
freyr_ult = Vision("deer\\freyr_ult.png")
meg_1 = Vision("deer\\meg_1.png")
meg_2 = Vision("deer\\meg_2.png")
meg_ult = Vision("deer\\meg_ult.png")
hel_1 = Vision("deer\\hel_1.png")
hel_2 = Vision("deer\\hel_2.png")
hel_ult = Vision("deer\\hel_ult.png")
tyr_1 = Vision("deer\\tyr_1.png")
tyr_2 = Vision("deer\\tyr_2.png")
tyr_ult = Vision("deer\\tyr_ult.png")

# For Dogs
empty_slot_1 = Vision("dogs\\empty_slot_1.png")
empty_slot_2 = Vision("dogs\\empty_slot_2.png")
empty_slot_3 = Vision("dogs\\empty_slot_3.png")
empty_slot_4 = Vision("dogs\\empty_slot_4.png")
empty_slot_5 = Vision("dogs\\empty_slot_5.png")
empty_slot_6 = Vision("dogs\\empty_slot_6.png")
empty_slot_7 = Vision("dogs\\empty_slot_7.png")
empty_slot_8 = Vision("dogs\\empty_slot_8.png")
empty_slot_9 = Vision("dogs\\empty_slot_9.png")
empty_slot_10 = Vision("dogs\\empty_slot_10.png")
empty_slot_11 = Vision("dogs\\empty_slot_11.png")
empty_slot_12 = Vision("dogs\\empty_slot_12.png")
empty_slot_13 = Vision("dogs\\empty_slot_13.png")
empty_slot_14 = Vision("dogs\\empty_slot_14.png")
empty_slot_15 = Vision("dogs\\empty_slot_15.png")
empty_slot_16 = Vision("dogs\\empty_slot_16.png")
empty_slot_17 = Vision("dogs\\empty_slot_17.png")
empty_slot_18 = Vision("dogs\\empty_slot_18.png")
# Dogs whale strat
freeze_icon = Vision("dogs\\freeze_icon.png")
lolimerl_aoe = Vision("dogs\\lolimerl_aoe.png")
lolimerl_st = Vision("dogs\\lolimerl_st.png")
lolimerl_ult = Vision("dogs\\lolimerl_ult.png")
milim_st = Vision("dogs\\milim_st.png")
milim_aoe = Vision("dogs\\milim_aoe.png")
milim_ult = Vision("dogs\\milim_ult.png")
unv_ghel_aoe1 = Vision("dogs\\unv_ghel_aoe1.png")
unv_ghel_aoe2 = Vision("dogs\\unv_ghel_aoe2.png")
unv_ghel_ult = Vision("dogs\\unv_ghel_ult.png")
unv_lolimerl_aoe = Vision("dogs\\unv_lolimerl_aoe.png")
unv_lolimerl_st = Vision("dogs\\unv_lolimerl_st.png")
unv_lolimerl_ult = Vision("dogs\\unv_lolimerl_ult.png")
unv_milim_st = Vision("dogs\\unv_milim_st.png")
unv_milim_aoe = Vision("dogs\\unv_milim_aoe.png")
unv_milim_ult = Vision("dogs\\unv_milim_ult.png")
unv_thor_1 = Vision("dogs\\unv_thor_1.png")
unv_thor_2 = Vision("dogs\\unv_thor_2.png")
unv_thor_ult = Vision("dogs\\unv_thor_ult.png")

# For Snake
nidhoggr = Vision("snake\\nidhoggr.png")
mael_st = Vision("snake\\mael_st.png")
mael_aoe = Vision("snake\\mael_aoe.png")
mael_ult = Vision("snake\\mael_ult.png")
margaret_st = Vision("snake\\margaret_st.png")
freyja_st = Vision("snake\\freyja_st.png")
freyja_aoe = Vision("snake\\freyja_aoe.png")
freyja_ult = Vision("snake\\freyja_ult.png")
lr_liz_aoe = Vision("snake\\lr_liz_aoe.png")
snake_stance = Vision("snake\\snake_stance.png")
snake_f3p2_counter = Vision("snake\\f3p2_counter.png")
extort = Vision("snake\\extort.png")
damage_increase = Vision("snake\\damage_increase.png")

# For final boss
final_boss_menu = Vision("final_boss\\final_boss_menu.png")
hell_difficulty = Vision("final_boss\\hell_difficulty.png")
challenge_difficulty = Vision("final_boss\\challenge_difficulty.png")
extreme_difficulty = Vision("final_boss\\extreme_difficulty.png")
hard_difficulty = Vision("final_boss\\hard_difficulty.png")
boss_destroyed = Vision("final_boss\\boss_destroyed.png")
boss_results = Vision("final_boss\\boss_results.png")
boss_mission = Vision("final_boss\\boss_mission.png")
episode_clear = Vision("final_boss\\episode_clear.png")
showdown = Vision("final_boss\\showdown.png")
fb_aut_off = Vision("final_boss\\auto_off.png")
failed = Vision("final_boss\\failed.png")


# For demon farming
boss_menu = Vision("demons\\demons.jpg")
red_demon = Vision("demons\\red_demon.png")
gray_demon = Vision("demons\\gray_demon.png")
crimson_demon = Vision("demons\\crimson_demon.png")
bell_demon = Vision("demons\\bell_demon.png")
og_demon = Vision("demons\\og_demon.png")
indura_demon = Vision("demons\\indura_demon.png")
accept_invitation = Vision("demons\\accept.png")
real_time = Vision("demons\\RT.png")
demon_hell_diff = Vision("demons\\hell.png")
demon_normal_diff = Vision("demons\\normal.png")
demon_hard_diff = Vision("demons\\hard.png")
demon_extreme_diff = Vision("demons\\extreme.png")
demon_chaos_diff = Vision("demons\\chaos.png")
cancel_realtime = Vision("demons\\cancel.png")
demons_loading_screen = Vision("demons\\demons_loading_screen.png")
join_request = Vision("demons\\join_request.png")
preparation_incomplete = Vision("demons\\preparation_incomplete.png")
cancel_preparation = Vision("demons\\cancel_preparation.png")
demons_auto = Vision("demons\\auto.jpg")
demons_destroyed = Vision("demons\\demons_destroyed.png")
# For Indura
king_att = Vision("demons\\king_att.png")
king_heal = Vision("demons\\king_heal.png")
indura_empty_slot = Vision("demons\\indura_empty_slot.png")
melee_evasion = Vision("demons\\melee_evasion.png")
ranged_evasion = Vision("demons\\ranged_evasion.png")
oxidize_indura = Vision("demons\\oxidize_indura.png")
king_unit = Vision("demons\\king_unit.png")
lancelot_unit = Vision("demons\\lancelot_unit.png")
alpha_unit = Vision("demons\\alpha_unit.png")
new_freyr_unit = Vision("demons\\new_freyr_unit.png")
mini_king = Vision("demons\\mini_king.png")
mini_heal = Vision("demons\\mini_heal.png")
mini_beta_buf = Vision("demons\\mini_beta_buf.png")
indura_tier = Vision("demons\\indura_tier.png")  # For phase 2 of Chaos!
alpha_ult = Vision("demons\\alpha_ult.png")
alpha_buff = Vision("demons\\alpha_buff.png")
lance_att = Vision("demons\\lance_att.png")
alpha_att = Vision("demons\\alpha_att.png")


# For dailies
go_now = Vision("dailies\\go_now.png")
coins_shop = Vision("dailies\\coins.png")
mail = Vision("dailies\\mail.png")
pvp_mode = Vision("dailies\\pvp_mode.png")
daily_quest_info = Vision("dailies\\quest_info.png")
daily_result = Vision("dailies\\result.png")
shop = Vision("dailies\\shop.png")
auto_clear = Vision("dailies\\auto_clear.png")
strart_auto_clear = Vision("dailies\\start_auto_clear.png")
quests = Vision("dailies\\quests.png")
daily_pvp = MultiVision("dailies\\daily_pvp.png", "dailies\\daily_pvp_new.png", image_name="daily_pvp")
daily_boss_battle = Vision("dailies\\daily_boss_battle.png")
daily_fort_solgress = MultiVision(
    "dailies\\daily_fort_solgress.png", "dailies\\daily_fort_solgress_new.png", image_name="daily_fort_solgress"
)
daily_friendship_coins = MultiVision(
    "dailies\\daily_friendship_coins.png",
    "dailies\\daily_friendship_coins_new.png",
    image_name="daily_friendship_coins",
)
daily_patrol = MultiVision("dailies\\daily_patrol.png", "dailies\\daily_patrol_new.png", image_name="daily_patrol")
daily_vanya_ale = MultiVision(
    "dailies\\daily_vanya_ale.png", "dailies\\daily_vanya_ale_new.png", image_name="daily_vanya_ale"
)
take_all_rewards = Vision("dailies\\take_all.png")
tasks = Vision("dailies\\tasks.png")
daily_tasks = Vision("dailies\\daily_tasks.png")
daily_complete = Vision("dailies\\complete.png")
fortune_card = Vision("dailies\\fortune_card.png")
blue_stone = Vision("dailies\\blue_stone.png")
search_for_a_kh = Vision("dailies\\search_for_a_kh.png")
participate = Vision("dailies\\participate.png")
# Daily boss fight
boss_battle = Vision("dailies\\boss_battle.png")
normal_diff_boss_battle = Vision("dailies\\normal_difficulty.png")
plus_auto_ticket = Vision("dailies\\plus_auto_ticket.png")
# Patrol
claim_reward = Vision("dailies\\claim_reward.png")
complete_all = Vision("dailies\\complete_all.png")
reward = Vision("dailies\\patrol_reward.png", image_name="reward")
set_all_patrol = Vision("dailies\\set_all.png")
patrol_all = Vision("dailies\\patrol_all.png")
patrol_dispatched = Vision("dailies\\patrol_dispatched.png")
# Fort Solgress
fort_solgress_special = Vision("dailies\\fs_special.png")
fs_event_dungeon = Vision("dailies\\event_dungeon.png")
fs_special_6th_floor = Vision("dailies\\6th_floor.png")
minus_auto_ticket = Vision("dailies\\minus_auto_ticket.png")
not_enough_dungeon_keys = Vision("dailies\\not_enough_dungeon_keys.png")
event_special_fs_dungeon = Vision("dailies\\event_special_fs_dungeon.png")
event_special_fs_battle = Vision("dailies\\event_special_fs_battle.png")
ad_wheel_free = Vision("dailies\\ad_wheel_free.png")
ad_wheel_play = Vision("dailies\\ad_wheel_play.png")
# Friendship coins
send_friendship_coins = Vision("dailies\\send_friendship_coins.png")
claim_all = Vision("dailies\\claim_all.png")
exit_cross = Vision("dailies\\exit_cross.png")
# Vanya ale
meli_affection = Vision("dailies\\meli_affection.png")
perci_affection = Vision("dailies\\perci_affection.png")
# Brawl
brawl = Vision("dailies\\brawl.png")
receive_brawl = Vision("dailies\\receive_brawl.png")
receive_brawl_extended = Vision("dailies\\receive_brawl_extended.png")
view_pvp_results = Vision("dailies\\view_results.png")
join_all = Vision("dailies\\join_all.png")
ready_up_brawl = Vision("dailies\\ready_up_brawl.png")
battle_brawl = Vision("dailies\\battle_brawl.png")
# PVP
search_pvp_match = Vision("dailies\\search_pvp_match.png")
tier_up_failed = Vision("dailies\\tier_up_failed.png")
tier_up_successful = Vision("dailies\\tier_up_successful.png")

# For weeklies
kh_boss_battle = Vision("weeklies\\kh_boss_battle.png")


# Create a single OkVision instance for all OK buttons
ok_main_button = MultiVision(
    "ok_buttons\\ok_button.jpg",
    "ok_buttons\\OK_save_party.png",
    "ok_buttons\\ok_bird_defeat.png",
    "ok_buttons\\fb_ok_button.png",
    "ok_buttons\\ok_pvp_defeat.png",
    "ok_buttons\\salvage_ok.png",
    "ok_buttons\\bird_okay.png",
    "ok_buttons\\finished_fight_ok.png",
    "ok_buttons\\forfeit_fight_ok.png",
    "ok_buttons\\demon_ok.jpg",
    "ok_buttons\\dead_ok.jpg",
    "ok_buttons\\kicked_ok.png",
    "ok_buttons\\ok_maintenance.png",
    image_name="Ok button",
)
