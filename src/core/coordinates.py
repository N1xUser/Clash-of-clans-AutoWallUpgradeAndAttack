class AttackCoordinates:
    ATTACK_BUTTON = {"x": 0.06, "y": 0.88, "w": 0.08, "h": 0.08}
    
    FIND_MATCH_BUTTON = {"x": 0.14, "y": 0.70, "w": 0.15, "h": 0.06}
    
    NEXT_BUTTON = {"x": 0.870, "y": 0.743, "w": 0.10, "h": 0.06}
    
    RETURN_HOME_BUTTON = {"x": 0.505, "y": 0.850, "w": 0, "h": 0}
    
    BATTLE_END_CHECK_POINT_1 = {"x": 0.872, "y": 0.463}
    BATTLE_END_CHECK_POINT_2 = {"x": 0.158, "y": 0.561}
    
    DONATE_MEDAL_BUTTON = {"x": 0.802, "y": 0.774, "w": 0.0, "h": 0.0}
    DONATE_CONFIRM_BUTTON = {"x": 0.675, "y": 0.666, "w": 0.00, "h": 0.0}
    DONATE_FINAL_BUTTON = {"x": 0.850, "y": 0.850, "w": 0.0, "h": 0.0}
    
    SKIP_DONATE_BUTTON = {"x": 0.85, "y": 0.85, "w": 0.0, "h": 0.0}
    
    SPELL_DEPLOY_MIN_X = 0.35
    SPELL_DEPLOY_MAX_X = 0.65
    SPELL_DEPLOY_MIN_Y = 0.35
    SPELL_DEPLOY_MAX_Y = 0.65
    
    DEPLOYMENT_SEGMENTS = [
        (0.161, 0.368, 0.364, 0.077),
        (0.615, 0.057, 0.812, 0.338),
        (0.821, 0.578, 0.681, 0.799),
        (0.251, 0.710, 0.184, 0.611)
    ]


class UpgradeCoordinates:
    WALL_VERIFY_CENTER_X = 0.481
    WALL_VERIFY_CENTER_Y = 0.794
    
    WALL_ADD_MORE = {"x": 0.467, "y": 0.802, "w": 0.0, "h": 0.0}
    
    UPGRADE_BUTTON_GOLD = {"x": 0.550, "y": 0.793, "w": 0.0, "h": 0.0}
    UPGRADE_BUTTON_ELIXIR = {"x": 0.628, "y": 0.804, "w": 0.0, "h": 0.0}
    
    CONFIRM_BUTTON_SINGLE = {"x": 0.714, "y": 0.856, "w": 0.0, "h": 0.0}
    CONFIRM_BUTTON_MULTI = {"x": 0.602, "y": 0.620, "w": 0.0, "h": 0.0}
    
    ELIXIR_COST_THRESHOLD = 500000


class MenuCoordinates:
    CORNER_TOP_RIGHT = {"x": 0.95, "y": 0.05, "w": 0, "h": 0}
    
    CLOSE_MENU = {"x": 0.1, "y": 0.5, "w": 0, "h": 0}
    
    BUILDER_MENU_SCROLL_FACTOR_START = 0.3
    BUILDER_MENU_SCROLL_FACTOR_END = 0.8
