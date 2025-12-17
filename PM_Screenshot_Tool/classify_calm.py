# Calm App 精细分类 - 基于产品经理视角逐张分析
# 120张截图全部手动审核后的分类结果

import os
import shutil

PROJECT_PATH = r"C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\projects\Calm_Analysis"
DOWNLOADS = os.path.join(PROJECT_PATH, "Downloads")
SCREENS = os.path.join(PROJECT_PATH, "screens")

# 清空并重建screens目录
if os.path.exists(SCREENS):
    shutil.rmtree(SCREENS)
os.makedirs(SCREENS)

# 精细分类映射 - 每张截图都经过审核
# 格式: 原始编号 -> (阶段编号, 阶段名, 步骤描述)
CLASSIFICATION = {
    # ========== ONBOARDING FLOW (001-015) ==========
    1: ("01", "Launch", "BreathingGuide"),           # take a deep breath
    2: ("02", "Permission", "Notification"),          # 通知权限
    3: ("02", "Permission", "ATT"),                   # 追踪权限
    4: ("03", "Onboarding", "GoalSelection"),         # What brings you to Calm
    5: ("04", "SignUp", "Entry"),                     # 注册入口
    6: ("04", "SignUp", "Form"),                      # 注册表单填写
    7: ("05", "Paywall", "Main"),                     # 付费墙主页
    8: ("05", "Paywall", "AppStoreConfirm"),          # App Store确认
    9: ("05", "Paywall", "PurchaseSuccess"),          # 购买成功
    10: ("05", "Paywall", "PremiumActivated"),        # Premium激活
    11: ("03", "Onboarding", "Attribution"),          # 渠道来源问卷
    
    # ========== REFERRAL (012-015) ==========
    12: ("06", "Referral", "PopupHome"),              # 推荐弹窗
    13: ("06", "Referral", "MainPage"),               # 推荐计划主页
    14: ("06", "Referral", "ShareSheet"),             # 分享面板
    15: ("06", "Referral", "ShareSuccess"),           # 分享成功
    
    # ========== HOME & ONBOARDING TASKS (016-020) ==========
    16: ("07", "Home", "TaskGuide"),                  # 首页任务引导
    17: ("08", "Feature_Scenes", "List"),             # 场景列表
    18: ("08", "Feature_Scenes", "TimePicker"),       # 时间选择
    19: ("08", "Feature_Scenes", "Preview"),          # 场景预览
    20: ("08", "Feature_Scenes", "Selected"),         # 场景选中
    
    # ========== DAILY PRACTICE (021) ==========
    21: ("09", "Feature_Daily", "PracticeList"),      # 每日练习列表
    
    # ========== PLAYER (022-031) ==========
    22: ("10", "Player", "Controls"),                 # 播放器控制
    23: ("10", "Player", "AirPlay"),                  # AirPlay
    24: ("10", "Player", "ShareSheet"),               # 分享面板
    25: ("10", "Player", "ShareSuccess"),             # 分享成功
    26: ("11", "Engagement", "RatingRequest"),        # 评分请求
    27: ("11", "Engagement", "RatingConfirm"),        # 评分确认
    28: ("10", "Player", "MoreOptions"),              # 更多选项
    29: ("10", "Player", "SpeedOptions"),             # 播放速度
    30: ("10", "Player", "AudioOptions"),             # 音频选项
    31: ("10", "Player", "SubtitleOptions"),          # 字幕选项
    
    # ========== POST SESSION (032-033) ==========
    32: ("12", "PostSession", "Complete"),            # 完成页
    33: ("12", "PostSession", "ShareSheet"),          # 完成后分享
    
    # ========== REMINDER (034-035) ==========
    34: ("13", "Feature_Reminder", "TimePicker"),     # 提醒时间选择
    35: ("13", "Feature_Reminder", "Setup"),          # 提醒设置
    
    # ========== MOOD CHECK-IN (036-040) ==========
    36: ("14", "Feature_MoodCheckIn", "PreSession"),  # 冥想前检查
    37: ("14", "Feature_MoodCheckIn", "Intro1"),      # 功能介绍1
    38: ("14", "Feature_MoodCheckIn", "Intro2"),      # 功能介绍2
    39: ("14", "Feature_MoodCheckIn", "EmojiSelect"), # 情绪选择
    40: ("14", "Feature_MoodCheckIn", "TagSelect"),   # 标签选择
    
    # ========== PLAYER DETAIL (041-051) ==========
    41: ("10", "Player", "DetailPage"),               # 播放详情页
    42: ("10", "Player", "RatingModal"),              # 推荐弹窗
    43: ("10", "Player", "ShareSheet2"),              # 分享面板
    44: ("15", "Feature_Playlist", "Create"),         # 创建播放列表
    45: ("15", "Feature_Playlist", "AddedSuccess"),   # 添加成功
    46: ("15", "Feature_Playlist", "SelectList"),     # 选择列表
    47: ("16", "Settings", "Sound"),                  # 声音设置
    48: ("17", "Content", "NarratorProfile"),         # 讲述者简介
    49: ("10", "Player", "ShareHint"),                # 分享提示
    50: ("10", "Player", "ShareSheet3"),              # 分享面板
    51: ("10", "Player", "ShareSuccess2"),            # 分享成功
    
    # ========== CONTENT BROWSE - MEDITATION (052-064) ==========
    52: ("18", "Content_Meditation", "CategoryAll"),
    53: ("18", "Content_Meditation", "CategorySleep"),
    54: ("18", "Content_Meditation", "CategoryAnxiety"),
    55: ("18", "Content_Meditation", "Featured"),
    56: ("18", "Content_Meditation", "RecentlyPlayed"),
    57: ("18", "Content_Meditation", "QuickList"),
    58: ("18", "Content_Meditation", "BeginnersList"),
    59: ("18", "Content_Meditation", "WithSoundscapes"),
    60: ("18", "Content_Meditation", "InnerPeace"),
    61: ("18", "Content_Meditation", "FocusList"),
    62: ("18", "Content_Meditation", "EmotionsList"),
    63: ("18", "Content_Meditation", "BodyList"),
    64: ("18", "Content_Meditation", "RelationshipList"),
    
    # ========== CONTENT BROWSE - SLEEP (065-079) ==========
    65: ("19", "Content_Sleep", "ByNarrator"),
    66: ("19", "Content_Sleep", "StoryList"),
    67: ("19", "Content_Sleep", "MusicList"),
    68: ("19", "Content_Sleep", "SoundscapesList"),
    69: ("19", "Content_Sleep", "PlaylistsList"),
    70: ("19", "Content_Sleep", "DownloadsEmpty"),
    71: ("19", "Content_Sleep", "StoryDetail"),
    72: ("19", "Content_Sleep", "StoryPlayer"),
    73: ("19", "Content_Sleep", "StoryPlayerOptions"),
    74: ("19", "Content_Sleep", "StoryShareHint"),
    75: ("19", "Content_Sleep", "StoryRating"),
    76: ("19", "Content_Sleep", "StoryComplete"),
    77: ("19", "Content_Sleep", "StoryShareSheet"),
    78: ("19", "Content_Sleep", "ToolsList"),
    79: ("19", "Content_Sleep", "ToolDetail"),
    
    # ========== DISCOVER TAB (080-084) ==========
    80: ("20", "Discover", "MainPage"),
    81: ("20", "Discover", "SearchResults"),
    82: ("20", "Discover", "CategoryBrowse"),
    83: ("20", "Discover", "CollectionView"),
    84: ("20", "Discover", "ShareAchievement"),
    
    # ========== PROFILE - JOURNAL (085-094) ==========
    85: ("21", "Profile_Journal", "EntriesList"),
    86: ("21", "Profile_Journal", "NewEntry"),
    87: ("21", "Profile_Journal", "EntryDetail"),
    88: ("21", "Profile_Journal", "EditEntry"),
    89: ("21", "Profile_Journal", "DeleteConfirm"),
    90: ("22", "Profile_Reflection", "TodayPrompt"),
    91: ("22", "Profile_Reflection", "WriteReflection"),
    92: ("22", "Profile_Reflection", "SavedReflection"),
    93: ("23", "Profile_Wisdom", "DailyQuote"),
    94: ("23", "Profile_Wisdom", "QuoteShare"),
    95: ("23", "Profile_Wisdom", "QuoteShareSheet"),
    
    # ========== PROFILE - STATS & CHECK-INS (096-104) ==========
    96: ("24", "Profile_Stats", "Overview"),
    97: ("24", "Profile_Stats", "StreakDetail"),
    98: ("24", "Profile_Stats", "MindfulMinutes"),
    99: ("25", "Profile_CheckIn", "MoodHistory"),
    100: ("25", "Profile_CheckIn", "GratitudeEmpty"),
    101: ("25", "Profile_CheckIn", "GratitudeEntry"),
    102: ("25", "Profile_CheckIn", "SleepCheckIn"),
    103: ("26", "Profile_Account", "Overview"),
    104: ("26", "Profile_Account", "EditProfile"),
    
    # ========== SETTINGS (105-120) ==========
    105: ("27", "Settings", "SubscriptionInfo"),
    106: ("27", "Settings", "ManageSubscription"),
    107: ("27", "Settings", "RestorePurchases"),
    108: ("27", "Settings", "RestoreSuccess"),
    109: ("28", "Settings", "NotificationsList"),
    110: ("28", "Settings", "NotificationsDetail"),
    111: ("28", "Settings", "ReminderEdit"),
    112: ("28", "Settings", "BedtimeReminder"),
    113: ("29", "Settings", "PrivacyOptions"),
    114: ("29", "Settings", "DataExport"),
    115: ("29", "Settings", "HealthAccess"),
    116: ("30", "Settings", "LanguageSelect"),
    117: ("30", "Settings", "HelpCenter"),
    118: ("30", "Settings", "About"),
    119: ("30", "Settings", "Logout"),
    120: ("30", "Settings", "MainPage"),
}

def classify():
    """执行分类"""
    count = 0
    for i in range(1, 121):
        src = os.path.join(DOWNLOADS, f"Screen_{i:03d}.png")
        if not os.path.exists(src):
            print(f"[WARN] Not found: {src}")
            continue
        
        if i in CLASSIFICATION:
            phase_num, phase_name, step_desc = CLASSIFICATION[i]
            new_name = f"{phase_num}_{phase_name}_{step_desc}.png"
        else:
            # 未分类的保持原名
            new_name = f"99_Uncategorized_{i:03d}.png"
        
        dst = os.path.join(SCREENS, new_name)
        
        # 处理重名
        if os.path.exists(dst):
            base, ext = os.path.splitext(new_name)
            j = 2
            while os.path.exists(os.path.join(SCREENS, f"{base}_{j}{ext}")):
                j += 1
            new_name = f"{base}_{j}{ext}"
            dst = os.path.join(SCREENS, new_name)
        
        shutil.copy2(src, dst)
        count += 1
        print(f"[OK] {i:03d} -> {new_name}")
    
    print(f"\nDone! {count} screenshots classified")
    print(f"Output: {SCREENS}")

if __name__ == "__main__":
    classify()



import os
import shutil

PROJECT_PATH = r"C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\projects\Calm_Analysis"
DOWNLOADS = os.path.join(PROJECT_PATH, "Downloads")
SCREENS = os.path.join(PROJECT_PATH, "screens")

# 清空并重建screens目录
if os.path.exists(SCREENS):
    shutil.rmtree(SCREENS)
os.makedirs(SCREENS)

# 精细分类映射 - 每张截图都经过审核
# 格式: 原始编号 -> (阶段编号, 阶段名, 步骤描述)
CLASSIFICATION = {
    # ========== ONBOARDING FLOW (001-015) ==========
    1: ("01", "Launch", "BreathingGuide"),           # take a deep breath
    2: ("02", "Permission", "Notification"),          # 通知权限
    3: ("02", "Permission", "ATT"),                   # 追踪权限
    4: ("03", "Onboarding", "GoalSelection"),         # What brings you to Calm
    5: ("04", "SignUp", "Entry"),                     # 注册入口
    6: ("04", "SignUp", "Form"),                      # 注册表单填写
    7: ("05", "Paywall", "Main"),                     # 付费墙主页
    8: ("05", "Paywall", "AppStoreConfirm"),          # App Store确认
    9: ("05", "Paywall", "PurchaseSuccess"),          # 购买成功
    10: ("05", "Paywall", "PremiumActivated"),        # Premium激活
    11: ("03", "Onboarding", "Attribution"),          # 渠道来源问卷
    
    # ========== REFERRAL (012-015) ==========
    12: ("06", "Referral", "PopupHome"),              # 推荐弹窗
    13: ("06", "Referral", "MainPage"),               # 推荐计划主页
    14: ("06", "Referral", "ShareSheet"),             # 分享面板
    15: ("06", "Referral", "ShareSuccess"),           # 分享成功
    
    # ========== HOME & ONBOARDING TASKS (016-020) ==========
    16: ("07", "Home", "TaskGuide"),                  # 首页任务引导
    17: ("08", "Feature_Scenes", "List"),             # 场景列表
    18: ("08", "Feature_Scenes", "TimePicker"),       # 时间选择
    19: ("08", "Feature_Scenes", "Preview"),          # 场景预览
    20: ("08", "Feature_Scenes", "Selected"),         # 场景选中
    
    # ========== DAILY PRACTICE (021) ==========
    21: ("09", "Feature_Daily", "PracticeList"),      # 每日练习列表
    
    # ========== PLAYER (022-031) ==========
    22: ("10", "Player", "Controls"),                 # 播放器控制
    23: ("10", "Player", "AirPlay"),                  # AirPlay
    24: ("10", "Player", "ShareSheet"),               # 分享面板
    25: ("10", "Player", "ShareSuccess"),             # 分享成功
    26: ("11", "Engagement", "RatingRequest"),        # 评分请求
    27: ("11", "Engagement", "RatingConfirm"),        # 评分确认
    28: ("10", "Player", "MoreOptions"),              # 更多选项
    29: ("10", "Player", "SpeedOptions"),             # 播放速度
    30: ("10", "Player", "AudioOptions"),             # 音频选项
    31: ("10", "Player", "SubtitleOptions"),          # 字幕选项
    
    # ========== POST SESSION (032-033) ==========
    32: ("12", "PostSession", "Complete"),            # 完成页
    33: ("12", "PostSession", "ShareSheet"),          # 完成后分享
    
    # ========== REMINDER (034-035) ==========
    34: ("13", "Feature_Reminder", "TimePicker"),     # 提醒时间选择
    35: ("13", "Feature_Reminder", "Setup"),          # 提醒设置
    
    # ========== MOOD CHECK-IN (036-040) ==========
    36: ("14", "Feature_MoodCheckIn", "PreSession"),  # 冥想前检查
    37: ("14", "Feature_MoodCheckIn", "Intro1"),      # 功能介绍1
    38: ("14", "Feature_MoodCheckIn", "Intro2"),      # 功能介绍2
    39: ("14", "Feature_MoodCheckIn", "EmojiSelect"), # 情绪选择
    40: ("14", "Feature_MoodCheckIn", "TagSelect"),   # 标签选择
    
    # ========== PLAYER DETAIL (041-051) ==========
    41: ("10", "Player", "DetailPage"),               # 播放详情页
    42: ("10", "Player", "RatingModal"),              # 推荐弹窗
    43: ("10", "Player", "ShareSheet2"),              # 分享面板
    44: ("15", "Feature_Playlist", "Create"),         # 创建播放列表
    45: ("15", "Feature_Playlist", "AddedSuccess"),   # 添加成功
    46: ("15", "Feature_Playlist", "SelectList"),     # 选择列表
    47: ("16", "Settings", "Sound"),                  # 声音设置
    48: ("17", "Content", "NarratorProfile"),         # 讲述者简介
    49: ("10", "Player", "ShareHint"),                # 分享提示
    50: ("10", "Player", "ShareSheet3"),              # 分享面板
    51: ("10", "Player", "ShareSuccess2"),            # 分享成功
    
    # ========== CONTENT BROWSE - MEDITATION (052-064) ==========
    52: ("18", "Content_Meditation", "CategoryAll"),
    53: ("18", "Content_Meditation", "CategorySleep"),
    54: ("18", "Content_Meditation", "CategoryAnxiety"),
    55: ("18", "Content_Meditation", "Featured"),
    56: ("18", "Content_Meditation", "RecentlyPlayed"),
    57: ("18", "Content_Meditation", "QuickList"),
    58: ("18", "Content_Meditation", "BeginnersList"),
    59: ("18", "Content_Meditation", "WithSoundscapes"),
    60: ("18", "Content_Meditation", "InnerPeace"),
    61: ("18", "Content_Meditation", "FocusList"),
    62: ("18", "Content_Meditation", "EmotionsList"),
    63: ("18", "Content_Meditation", "BodyList"),
    64: ("18", "Content_Meditation", "RelationshipList"),
    
    # ========== CONTENT BROWSE - SLEEP (065-079) ==========
    65: ("19", "Content_Sleep", "ByNarrator"),
    66: ("19", "Content_Sleep", "StoryList"),
    67: ("19", "Content_Sleep", "MusicList"),
    68: ("19", "Content_Sleep", "SoundscapesList"),
    69: ("19", "Content_Sleep", "PlaylistsList"),
    70: ("19", "Content_Sleep", "DownloadsEmpty"),
    71: ("19", "Content_Sleep", "StoryDetail"),
    72: ("19", "Content_Sleep", "StoryPlayer"),
    73: ("19", "Content_Sleep", "StoryPlayerOptions"),
    74: ("19", "Content_Sleep", "StoryShareHint"),
    75: ("19", "Content_Sleep", "StoryRating"),
    76: ("19", "Content_Sleep", "StoryComplete"),
    77: ("19", "Content_Sleep", "StoryShareSheet"),
    78: ("19", "Content_Sleep", "ToolsList"),
    79: ("19", "Content_Sleep", "ToolDetail"),
    
    # ========== DISCOVER TAB (080-084) ==========
    80: ("20", "Discover", "MainPage"),
    81: ("20", "Discover", "SearchResults"),
    82: ("20", "Discover", "CategoryBrowse"),
    83: ("20", "Discover", "CollectionView"),
    84: ("20", "Discover", "ShareAchievement"),
    
    # ========== PROFILE - JOURNAL (085-094) ==========
    85: ("21", "Profile_Journal", "EntriesList"),
    86: ("21", "Profile_Journal", "NewEntry"),
    87: ("21", "Profile_Journal", "EntryDetail"),
    88: ("21", "Profile_Journal", "EditEntry"),
    89: ("21", "Profile_Journal", "DeleteConfirm"),
    90: ("22", "Profile_Reflection", "TodayPrompt"),
    91: ("22", "Profile_Reflection", "WriteReflection"),
    92: ("22", "Profile_Reflection", "SavedReflection"),
    93: ("23", "Profile_Wisdom", "DailyQuote"),
    94: ("23", "Profile_Wisdom", "QuoteShare"),
    95: ("23", "Profile_Wisdom", "QuoteShareSheet"),
    
    # ========== PROFILE - STATS & CHECK-INS (096-104) ==========
    96: ("24", "Profile_Stats", "Overview"),
    97: ("24", "Profile_Stats", "StreakDetail"),
    98: ("24", "Profile_Stats", "MindfulMinutes"),
    99: ("25", "Profile_CheckIn", "MoodHistory"),
    100: ("25", "Profile_CheckIn", "GratitudeEmpty"),
    101: ("25", "Profile_CheckIn", "GratitudeEntry"),
    102: ("25", "Profile_CheckIn", "SleepCheckIn"),
    103: ("26", "Profile_Account", "Overview"),
    104: ("26", "Profile_Account", "EditProfile"),
    
    # ========== SETTINGS (105-120) ==========
    105: ("27", "Settings", "SubscriptionInfo"),
    106: ("27", "Settings", "ManageSubscription"),
    107: ("27", "Settings", "RestorePurchases"),
    108: ("27", "Settings", "RestoreSuccess"),
    109: ("28", "Settings", "NotificationsList"),
    110: ("28", "Settings", "NotificationsDetail"),
    111: ("28", "Settings", "ReminderEdit"),
    112: ("28", "Settings", "BedtimeReminder"),
    113: ("29", "Settings", "PrivacyOptions"),
    114: ("29", "Settings", "DataExport"),
    115: ("29", "Settings", "HealthAccess"),
    116: ("30", "Settings", "LanguageSelect"),
    117: ("30", "Settings", "HelpCenter"),
    118: ("30", "Settings", "About"),
    119: ("30", "Settings", "Logout"),
    120: ("30", "Settings", "MainPage"),
}

def classify():
    """执行分类"""
    count = 0
    for i in range(1, 121):
        src = os.path.join(DOWNLOADS, f"Screen_{i:03d}.png")
        if not os.path.exists(src):
            print(f"[WARN] Not found: {src}")
            continue
        
        if i in CLASSIFICATION:
            phase_num, phase_name, step_desc = CLASSIFICATION[i]
            new_name = f"{phase_num}_{phase_name}_{step_desc}.png"
        else:
            # 未分类的保持原名
            new_name = f"99_Uncategorized_{i:03d}.png"
        
        dst = os.path.join(SCREENS, new_name)
        
        # 处理重名
        if os.path.exists(dst):
            base, ext = os.path.splitext(new_name)
            j = 2
            while os.path.exists(os.path.join(SCREENS, f"{base}_{j}{ext}")):
                j += 1
            new_name = f"{base}_{j}{ext}"
            dst = os.path.join(SCREENS, new_name)
        
        shutil.copy2(src, dst)
        count += 1
        print(f"[OK] {i:03d} -> {new_name}")
    
    print(f"\nDone! {count} screenshots classified")
    print(f"Output: {SCREENS}")

if __name__ == "__main__":
    classify()



import os
import shutil

PROJECT_PATH = r"C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\projects\Calm_Analysis"
DOWNLOADS = os.path.join(PROJECT_PATH, "Downloads")
SCREENS = os.path.join(PROJECT_PATH, "screens")

# 清空并重建screens目录
if os.path.exists(SCREENS):
    shutil.rmtree(SCREENS)
os.makedirs(SCREENS)

# 精细分类映射 - 每张截图都经过审核
# 格式: 原始编号 -> (阶段编号, 阶段名, 步骤描述)
CLASSIFICATION = {
    # ========== ONBOARDING FLOW (001-015) ==========
    1: ("01", "Launch", "BreathingGuide"),           # take a deep breath
    2: ("02", "Permission", "Notification"),          # 通知权限
    3: ("02", "Permission", "ATT"),                   # 追踪权限
    4: ("03", "Onboarding", "GoalSelection"),         # What brings you to Calm
    5: ("04", "SignUp", "Entry"),                     # 注册入口
    6: ("04", "SignUp", "Form"),                      # 注册表单填写
    7: ("05", "Paywall", "Main"),                     # 付费墙主页
    8: ("05", "Paywall", "AppStoreConfirm"),          # App Store确认
    9: ("05", "Paywall", "PurchaseSuccess"),          # 购买成功
    10: ("05", "Paywall", "PremiumActivated"),        # Premium激活
    11: ("03", "Onboarding", "Attribution"),          # 渠道来源问卷
    
    # ========== REFERRAL (012-015) ==========
    12: ("06", "Referral", "PopupHome"),              # 推荐弹窗
    13: ("06", "Referral", "MainPage"),               # 推荐计划主页
    14: ("06", "Referral", "ShareSheet"),             # 分享面板
    15: ("06", "Referral", "ShareSuccess"),           # 分享成功
    
    # ========== HOME & ONBOARDING TASKS (016-020) ==========
    16: ("07", "Home", "TaskGuide"),                  # 首页任务引导
    17: ("08", "Feature_Scenes", "List"),             # 场景列表
    18: ("08", "Feature_Scenes", "TimePicker"),       # 时间选择
    19: ("08", "Feature_Scenes", "Preview"),          # 场景预览
    20: ("08", "Feature_Scenes", "Selected"),         # 场景选中
    
    # ========== DAILY PRACTICE (021) ==========
    21: ("09", "Feature_Daily", "PracticeList"),      # 每日练习列表
    
    # ========== PLAYER (022-031) ==========
    22: ("10", "Player", "Controls"),                 # 播放器控制
    23: ("10", "Player", "AirPlay"),                  # AirPlay
    24: ("10", "Player", "ShareSheet"),               # 分享面板
    25: ("10", "Player", "ShareSuccess"),             # 分享成功
    26: ("11", "Engagement", "RatingRequest"),        # 评分请求
    27: ("11", "Engagement", "RatingConfirm"),        # 评分确认
    28: ("10", "Player", "MoreOptions"),              # 更多选项
    29: ("10", "Player", "SpeedOptions"),             # 播放速度
    30: ("10", "Player", "AudioOptions"),             # 音频选项
    31: ("10", "Player", "SubtitleOptions"),          # 字幕选项
    
    # ========== POST SESSION (032-033) ==========
    32: ("12", "PostSession", "Complete"),            # 完成页
    33: ("12", "PostSession", "ShareSheet"),          # 完成后分享
    
    # ========== REMINDER (034-035) ==========
    34: ("13", "Feature_Reminder", "TimePicker"),     # 提醒时间选择
    35: ("13", "Feature_Reminder", "Setup"),          # 提醒设置
    
    # ========== MOOD CHECK-IN (036-040) ==========
    36: ("14", "Feature_MoodCheckIn", "PreSession"),  # 冥想前检查
    37: ("14", "Feature_MoodCheckIn", "Intro1"),      # 功能介绍1
    38: ("14", "Feature_MoodCheckIn", "Intro2"),      # 功能介绍2
    39: ("14", "Feature_MoodCheckIn", "EmojiSelect"), # 情绪选择
    40: ("14", "Feature_MoodCheckIn", "TagSelect"),   # 标签选择
    
    # ========== PLAYER DETAIL (041-051) ==========
    41: ("10", "Player", "DetailPage"),               # 播放详情页
    42: ("10", "Player", "RatingModal"),              # 推荐弹窗
    43: ("10", "Player", "ShareSheet2"),              # 分享面板
    44: ("15", "Feature_Playlist", "Create"),         # 创建播放列表
    45: ("15", "Feature_Playlist", "AddedSuccess"),   # 添加成功
    46: ("15", "Feature_Playlist", "SelectList"),     # 选择列表
    47: ("16", "Settings", "Sound"),                  # 声音设置
    48: ("17", "Content", "NarratorProfile"),         # 讲述者简介
    49: ("10", "Player", "ShareHint"),                # 分享提示
    50: ("10", "Player", "ShareSheet3"),              # 分享面板
    51: ("10", "Player", "ShareSuccess2"),            # 分享成功
    
    # ========== CONTENT BROWSE - MEDITATION (052-064) ==========
    52: ("18", "Content_Meditation", "CategoryAll"),
    53: ("18", "Content_Meditation", "CategorySleep"),
    54: ("18", "Content_Meditation", "CategoryAnxiety"),
    55: ("18", "Content_Meditation", "Featured"),
    56: ("18", "Content_Meditation", "RecentlyPlayed"),
    57: ("18", "Content_Meditation", "QuickList"),
    58: ("18", "Content_Meditation", "BeginnersList"),
    59: ("18", "Content_Meditation", "WithSoundscapes"),
    60: ("18", "Content_Meditation", "InnerPeace"),
    61: ("18", "Content_Meditation", "FocusList"),
    62: ("18", "Content_Meditation", "EmotionsList"),
    63: ("18", "Content_Meditation", "BodyList"),
    64: ("18", "Content_Meditation", "RelationshipList"),
    
    # ========== CONTENT BROWSE - SLEEP (065-079) ==========
    65: ("19", "Content_Sleep", "ByNarrator"),
    66: ("19", "Content_Sleep", "StoryList"),
    67: ("19", "Content_Sleep", "MusicList"),
    68: ("19", "Content_Sleep", "SoundscapesList"),
    69: ("19", "Content_Sleep", "PlaylistsList"),
    70: ("19", "Content_Sleep", "DownloadsEmpty"),
    71: ("19", "Content_Sleep", "StoryDetail"),
    72: ("19", "Content_Sleep", "StoryPlayer"),
    73: ("19", "Content_Sleep", "StoryPlayerOptions"),
    74: ("19", "Content_Sleep", "StoryShareHint"),
    75: ("19", "Content_Sleep", "StoryRating"),
    76: ("19", "Content_Sleep", "StoryComplete"),
    77: ("19", "Content_Sleep", "StoryShareSheet"),
    78: ("19", "Content_Sleep", "ToolsList"),
    79: ("19", "Content_Sleep", "ToolDetail"),
    
    # ========== DISCOVER TAB (080-084) ==========
    80: ("20", "Discover", "MainPage"),
    81: ("20", "Discover", "SearchResults"),
    82: ("20", "Discover", "CategoryBrowse"),
    83: ("20", "Discover", "CollectionView"),
    84: ("20", "Discover", "ShareAchievement"),
    
    # ========== PROFILE - JOURNAL (085-094) ==========
    85: ("21", "Profile_Journal", "EntriesList"),
    86: ("21", "Profile_Journal", "NewEntry"),
    87: ("21", "Profile_Journal", "EntryDetail"),
    88: ("21", "Profile_Journal", "EditEntry"),
    89: ("21", "Profile_Journal", "DeleteConfirm"),
    90: ("22", "Profile_Reflection", "TodayPrompt"),
    91: ("22", "Profile_Reflection", "WriteReflection"),
    92: ("22", "Profile_Reflection", "SavedReflection"),
    93: ("23", "Profile_Wisdom", "DailyQuote"),
    94: ("23", "Profile_Wisdom", "QuoteShare"),
    95: ("23", "Profile_Wisdom", "QuoteShareSheet"),
    
    # ========== PROFILE - STATS & CHECK-INS (096-104) ==========
    96: ("24", "Profile_Stats", "Overview"),
    97: ("24", "Profile_Stats", "StreakDetail"),
    98: ("24", "Profile_Stats", "MindfulMinutes"),
    99: ("25", "Profile_CheckIn", "MoodHistory"),
    100: ("25", "Profile_CheckIn", "GratitudeEmpty"),
    101: ("25", "Profile_CheckIn", "GratitudeEntry"),
    102: ("25", "Profile_CheckIn", "SleepCheckIn"),
    103: ("26", "Profile_Account", "Overview"),
    104: ("26", "Profile_Account", "EditProfile"),
    
    # ========== SETTINGS (105-120) ==========
    105: ("27", "Settings", "SubscriptionInfo"),
    106: ("27", "Settings", "ManageSubscription"),
    107: ("27", "Settings", "RestorePurchases"),
    108: ("27", "Settings", "RestoreSuccess"),
    109: ("28", "Settings", "NotificationsList"),
    110: ("28", "Settings", "NotificationsDetail"),
    111: ("28", "Settings", "ReminderEdit"),
    112: ("28", "Settings", "BedtimeReminder"),
    113: ("29", "Settings", "PrivacyOptions"),
    114: ("29", "Settings", "DataExport"),
    115: ("29", "Settings", "HealthAccess"),
    116: ("30", "Settings", "LanguageSelect"),
    117: ("30", "Settings", "HelpCenter"),
    118: ("30", "Settings", "About"),
    119: ("30", "Settings", "Logout"),
    120: ("30", "Settings", "MainPage"),
}

def classify():
    """执行分类"""
    count = 0
    for i in range(1, 121):
        src = os.path.join(DOWNLOADS, f"Screen_{i:03d}.png")
        if not os.path.exists(src):
            print(f"[WARN] Not found: {src}")
            continue
        
        if i in CLASSIFICATION:
            phase_num, phase_name, step_desc = CLASSIFICATION[i]
            new_name = f"{phase_num}_{phase_name}_{step_desc}.png"
        else:
            # 未分类的保持原名
            new_name = f"99_Uncategorized_{i:03d}.png"
        
        dst = os.path.join(SCREENS, new_name)
        
        # 处理重名
        if os.path.exists(dst):
            base, ext = os.path.splitext(new_name)
            j = 2
            while os.path.exists(os.path.join(SCREENS, f"{base}_{j}{ext}")):
                j += 1
            new_name = f"{base}_{j}{ext}"
            dst = os.path.join(SCREENS, new_name)
        
        shutil.copy2(src, dst)
        count += 1
        print(f"[OK] {i:03d} -> {new_name}")
    
    print(f"\nDone! {count} screenshots classified")
    print(f"Output: {SCREENS}")

if __name__ == "__main__":
    classify()



import os
import shutil

PROJECT_PATH = r"C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\projects\Calm_Analysis"
DOWNLOADS = os.path.join(PROJECT_PATH, "Downloads")
SCREENS = os.path.join(PROJECT_PATH, "screens")

# 清空并重建screens目录
if os.path.exists(SCREENS):
    shutil.rmtree(SCREENS)
os.makedirs(SCREENS)

# 精细分类映射 - 每张截图都经过审核
# 格式: 原始编号 -> (阶段编号, 阶段名, 步骤描述)
CLASSIFICATION = {
    # ========== ONBOARDING FLOW (001-015) ==========
    1: ("01", "Launch", "BreathingGuide"),           # take a deep breath
    2: ("02", "Permission", "Notification"),          # 通知权限
    3: ("02", "Permission", "ATT"),                   # 追踪权限
    4: ("03", "Onboarding", "GoalSelection"),         # What brings you to Calm
    5: ("04", "SignUp", "Entry"),                     # 注册入口
    6: ("04", "SignUp", "Form"),                      # 注册表单填写
    7: ("05", "Paywall", "Main"),                     # 付费墙主页
    8: ("05", "Paywall", "AppStoreConfirm"),          # App Store确认
    9: ("05", "Paywall", "PurchaseSuccess"),          # 购买成功
    10: ("05", "Paywall", "PremiumActivated"),        # Premium激活
    11: ("03", "Onboarding", "Attribution"),          # 渠道来源问卷
    
    # ========== REFERRAL (012-015) ==========
    12: ("06", "Referral", "PopupHome"),              # 推荐弹窗
    13: ("06", "Referral", "MainPage"),               # 推荐计划主页
    14: ("06", "Referral", "ShareSheet"),             # 分享面板
    15: ("06", "Referral", "ShareSuccess"),           # 分享成功
    
    # ========== HOME & ONBOARDING TASKS (016-020) ==========
    16: ("07", "Home", "TaskGuide"),                  # 首页任务引导
    17: ("08", "Feature_Scenes", "List"),             # 场景列表
    18: ("08", "Feature_Scenes", "TimePicker"),       # 时间选择
    19: ("08", "Feature_Scenes", "Preview"),          # 场景预览
    20: ("08", "Feature_Scenes", "Selected"),         # 场景选中
    
    # ========== DAILY PRACTICE (021) ==========
    21: ("09", "Feature_Daily", "PracticeList"),      # 每日练习列表
    
    # ========== PLAYER (022-031) ==========
    22: ("10", "Player", "Controls"),                 # 播放器控制
    23: ("10", "Player", "AirPlay"),                  # AirPlay
    24: ("10", "Player", "ShareSheet"),               # 分享面板
    25: ("10", "Player", "ShareSuccess"),             # 分享成功
    26: ("11", "Engagement", "RatingRequest"),        # 评分请求
    27: ("11", "Engagement", "RatingConfirm"),        # 评分确认
    28: ("10", "Player", "MoreOptions"),              # 更多选项
    29: ("10", "Player", "SpeedOptions"),             # 播放速度
    30: ("10", "Player", "AudioOptions"),             # 音频选项
    31: ("10", "Player", "SubtitleOptions"),          # 字幕选项
    
    # ========== POST SESSION (032-033) ==========
    32: ("12", "PostSession", "Complete"),            # 完成页
    33: ("12", "PostSession", "ShareSheet"),          # 完成后分享
    
    # ========== REMINDER (034-035) ==========
    34: ("13", "Feature_Reminder", "TimePicker"),     # 提醒时间选择
    35: ("13", "Feature_Reminder", "Setup"),          # 提醒设置
    
    # ========== MOOD CHECK-IN (036-040) ==========
    36: ("14", "Feature_MoodCheckIn", "PreSession"),  # 冥想前检查
    37: ("14", "Feature_MoodCheckIn", "Intro1"),      # 功能介绍1
    38: ("14", "Feature_MoodCheckIn", "Intro2"),      # 功能介绍2
    39: ("14", "Feature_MoodCheckIn", "EmojiSelect"), # 情绪选择
    40: ("14", "Feature_MoodCheckIn", "TagSelect"),   # 标签选择
    
    # ========== PLAYER DETAIL (041-051) ==========
    41: ("10", "Player", "DetailPage"),               # 播放详情页
    42: ("10", "Player", "RatingModal"),              # 推荐弹窗
    43: ("10", "Player", "ShareSheet2"),              # 分享面板
    44: ("15", "Feature_Playlist", "Create"),         # 创建播放列表
    45: ("15", "Feature_Playlist", "AddedSuccess"),   # 添加成功
    46: ("15", "Feature_Playlist", "SelectList"),     # 选择列表
    47: ("16", "Settings", "Sound"),                  # 声音设置
    48: ("17", "Content", "NarratorProfile"),         # 讲述者简介
    49: ("10", "Player", "ShareHint"),                # 分享提示
    50: ("10", "Player", "ShareSheet3"),              # 分享面板
    51: ("10", "Player", "ShareSuccess2"),            # 分享成功
    
    # ========== CONTENT BROWSE - MEDITATION (052-064) ==========
    52: ("18", "Content_Meditation", "CategoryAll"),
    53: ("18", "Content_Meditation", "CategorySleep"),
    54: ("18", "Content_Meditation", "CategoryAnxiety"),
    55: ("18", "Content_Meditation", "Featured"),
    56: ("18", "Content_Meditation", "RecentlyPlayed"),
    57: ("18", "Content_Meditation", "QuickList"),
    58: ("18", "Content_Meditation", "BeginnersList"),
    59: ("18", "Content_Meditation", "WithSoundscapes"),
    60: ("18", "Content_Meditation", "InnerPeace"),
    61: ("18", "Content_Meditation", "FocusList"),
    62: ("18", "Content_Meditation", "EmotionsList"),
    63: ("18", "Content_Meditation", "BodyList"),
    64: ("18", "Content_Meditation", "RelationshipList"),
    
    # ========== CONTENT BROWSE - SLEEP (065-079) ==========
    65: ("19", "Content_Sleep", "ByNarrator"),
    66: ("19", "Content_Sleep", "StoryList"),
    67: ("19", "Content_Sleep", "MusicList"),
    68: ("19", "Content_Sleep", "SoundscapesList"),
    69: ("19", "Content_Sleep", "PlaylistsList"),
    70: ("19", "Content_Sleep", "DownloadsEmpty"),
    71: ("19", "Content_Sleep", "StoryDetail"),
    72: ("19", "Content_Sleep", "StoryPlayer"),
    73: ("19", "Content_Sleep", "StoryPlayerOptions"),
    74: ("19", "Content_Sleep", "StoryShareHint"),
    75: ("19", "Content_Sleep", "StoryRating"),
    76: ("19", "Content_Sleep", "StoryComplete"),
    77: ("19", "Content_Sleep", "StoryShareSheet"),
    78: ("19", "Content_Sleep", "ToolsList"),
    79: ("19", "Content_Sleep", "ToolDetail"),
    
    # ========== DISCOVER TAB (080-084) ==========
    80: ("20", "Discover", "MainPage"),
    81: ("20", "Discover", "SearchResults"),
    82: ("20", "Discover", "CategoryBrowse"),
    83: ("20", "Discover", "CollectionView"),
    84: ("20", "Discover", "ShareAchievement"),
    
    # ========== PROFILE - JOURNAL (085-094) ==========
    85: ("21", "Profile_Journal", "EntriesList"),
    86: ("21", "Profile_Journal", "NewEntry"),
    87: ("21", "Profile_Journal", "EntryDetail"),
    88: ("21", "Profile_Journal", "EditEntry"),
    89: ("21", "Profile_Journal", "DeleteConfirm"),
    90: ("22", "Profile_Reflection", "TodayPrompt"),
    91: ("22", "Profile_Reflection", "WriteReflection"),
    92: ("22", "Profile_Reflection", "SavedReflection"),
    93: ("23", "Profile_Wisdom", "DailyQuote"),
    94: ("23", "Profile_Wisdom", "QuoteShare"),
    95: ("23", "Profile_Wisdom", "QuoteShareSheet"),
    
    # ========== PROFILE - STATS & CHECK-INS (096-104) ==========
    96: ("24", "Profile_Stats", "Overview"),
    97: ("24", "Profile_Stats", "StreakDetail"),
    98: ("24", "Profile_Stats", "MindfulMinutes"),
    99: ("25", "Profile_CheckIn", "MoodHistory"),
    100: ("25", "Profile_CheckIn", "GratitudeEmpty"),
    101: ("25", "Profile_CheckIn", "GratitudeEntry"),
    102: ("25", "Profile_CheckIn", "SleepCheckIn"),
    103: ("26", "Profile_Account", "Overview"),
    104: ("26", "Profile_Account", "EditProfile"),
    
    # ========== SETTINGS (105-120) ==========
    105: ("27", "Settings", "SubscriptionInfo"),
    106: ("27", "Settings", "ManageSubscription"),
    107: ("27", "Settings", "RestorePurchases"),
    108: ("27", "Settings", "RestoreSuccess"),
    109: ("28", "Settings", "NotificationsList"),
    110: ("28", "Settings", "NotificationsDetail"),
    111: ("28", "Settings", "ReminderEdit"),
    112: ("28", "Settings", "BedtimeReminder"),
    113: ("29", "Settings", "PrivacyOptions"),
    114: ("29", "Settings", "DataExport"),
    115: ("29", "Settings", "HealthAccess"),
    116: ("30", "Settings", "LanguageSelect"),
    117: ("30", "Settings", "HelpCenter"),
    118: ("30", "Settings", "About"),
    119: ("30", "Settings", "Logout"),
    120: ("30", "Settings", "MainPage"),
}

def classify():
    """执行分类"""
    count = 0
    for i in range(1, 121):
        src = os.path.join(DOWNLOADS, f"Screen_{i:03d}.png")
        if not os.path.exists(src):
            print(f"[WARN] Not found: {src}")
            continue
        
        if i in CLASSIFICATION:
            phase_num, phase_name, step_desc = CLASSIFICATION[i]
            new_name = f"{phase_num}_{phase_name}_{step_desc}.png"
        else:
            # 未分类的保持原名
            new_name = f"99_Uncategorized_{i:03d}.png"
        
        dst = os.path.join(SCREENS, new_name)
        
        # 处理重名
        if os.path.exists(dst):
            base, ext = os.path.splitext(new_name)
            j = 2
            while os.path.exists(os.path.join(SCREENS, f"{base}_{j}{ext}")):
                j += 1
            new_name = f"{base}_{j}{ext}"
            dst = os.path.join(SCREENS, new_name)
        
        shutil.copy2(src, dst)
        count += 1
        print(f"[OK] {i:03d} -> {new_name}")
    
    print(f"\nDone! {count} screenshots classified")
    print(f"Output: {SCREENS}")

if __name__ == "__main__":
    classify()



import os
import shutil

PROJECT_PATH = r"C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\projects\Calm_Analysis"
DOWNLOADS = os.path.join(PROJECT_PATH, "Downloads")
SCREENS = os.path.join(PROJECT_PATH, "screens")

# 清空并重建screens目录
if os.path.exists(SCREENS):
    shutil.rmtree(SCREENS)
os.makedirs(SCREENS)

# 精细分类映射 - 每张截图都经过审核
# 格式: 原始编号 -> (阶段编号, 阶段名, 步骤描述)
CLASSIFICATION = {
    # ========== ONBOARDING FLOW (001-015) ==========
    1: ("01", "Launch", "BreathingGuide"),           # take a deep breath
    2: ("02", "Permission", "Notification"),          # 通知权限
    3: ("02", "Permission", "ATT"),                   # 追踪权限
    4: ("03", "Onboarding", "GoalSelection"),         # What brings you to Calm
    5: ("04", "SignUp", "Entry"),                     # 注册入口
    6: ("04", "SignUp", "Form"),                      # 注册表单填写
    7: ("05", "Paywall", "Main"),                     # 付费墙主页
    8: ("05", "Paywall", "AppStoreConfirm"),          # App Store确认
    9: ("05", "Paywall", "PurchaseSuccess"),          # 购买成功
    10: ("05", "Paywall", "PremiumActivated"),        # Premium激活
    11: ("03", "Onboarding", "Attribution"),          # 渠道来源问卷
    
    # ========== REFERRAL (012-015) ==========
    12: ("06", "Referral", "PopupHome"),              # 推荐弹窗
    13: ("06", "Referral", "MainPage"),               # 推荐计划主页
    14: ("06", "Referral", "ShareSheet"),             # 分享面板
    15: ("06", "Referral", "ShareSuccess"),           # 分享成功
    
    # ========== HOME & ONBOARDING TASKS (016-020) ==========
    16: ("07", "Home", "TaskGuide"),                  # 首页任务引导
    17: ("08", "Feature_Scenes", "List"),             # 场景列表
    18: ("08", "Feature_Scenes", "TimePicker"),       # 时间选择
    19: ("08", "Feature_Scenes", "Preview"),          # 场景预览
    20: ("08", "Feature_Scenes", "Selected"),         # 场景选中
    
    # ========== DAILY PRACTICE (021) ==========
    21: ("09", "Feature_Daily", "PracticeList"),      # 每日练习列表
    
    # ========== PLAYER (022-031) ==========
    22: ("10", "Player", "Controls"),                 # 播放器控制
    23: ("10", "Player", "AirPlay"),                  # AirPlay
    24: ("10", "Player", "ShareSheet"),               # 分享面板
    25: ("10", "Player", "ShareSuccess"),             # 分享成功
    26: ("11", "Engagement", "RatingRequest"),        # 评分请求
    27: ("11", "Engagement", "RatingConfirm"),        # 评分确认
    28: ("10", "Player", "MoreOptions"),              # 更多选项
    29: ("10", "Player", "SpeedOptions"),             # 播放速度
    30: ("10", "Player", "AudioOptions"),             # 音频选项
    31: ("10", "Player", "SubtitleOptions"),          # 字幕选项
    
    # ========== POST SESSION (032-033) ==========
    32: ("12", "PostSession", "Complete"),            # 完成页
    33: ("12", "PostSession", "ShareSheet"),          # 完成后分享
    
    # ========== REMINDER (034-035) ==========
    34: ("13", "Feature_Reminder", "TimePicker"),     # 提醒时间选择
    35: ("13", "Feature_Reminder", "Setup"),          # 提醒设置
    
    # ========== MOOD CHECK-IN (036-040) ==========
    36: ("14", "Feature_MoodCheckIn", "PreSession"),  # 冥想前检查
    37: ("14", "Feature_MoodCheckIn", "Intro1"),      # 功能介绍1
    38: ("14", "Feature_MoodCheckIn", "Intro2"),      # 功能介绍2
    39: ("14", "Feature_MoodCheckIn", "EmojiSelect"), # 情绪选择
    40: ("14", "Feature_MoodCheckIn", "TagSelect"),   # 标签选择
    
    # ========== PLAYER DETAIL (041-051) ==========
    41: ("10", "Player", "DetailPage"),               # 播放详情页
    42: ("10", "Player", "RatingModal"),              # 推荐弹窗
    43: ("10", "Player", "ShareSheet2"),              # 分享面板
    44: ("15", "Feature_Playlist", "Create"),         # 创建播放列表
    45: ("15", "Feature_Playlist", "AddedSuccess"),   # 添加成功
    46: ("15", "Feature_Playlist", "SelectList"),     # 选择列表
    47: ("16", "Settings", "Sound"),                  # 声音设置
    48: ("17", "Content", "NarratorProfile"),         # 讲述者简介
    49: ("10", "Player", "ShareHint"),                # 分享提示
    50: ("10", "Player", "ShareSheet3"),              # 分享面板
    51: ("10", "Player", "ShareSuccess2"),            # 分享成功
    
    # ========== CONTENT BROWSE - MEDITATION (052-064) ==========
    52: ("18", "Content_Meditation", "CategoryAll"),
    53: ("18", "Content_Meditation", "CategorySleep"),
    54: ("18", "Content_Meditation", "CategoryAnxiety"),
    55: ("18", "Content_Meditation", "Featured"),
    56: ("18", "Content_Meditation", "RecentlyPlayed"),
    57: ("18", "Content_Meditation", "QuickList"),
    58: ("18", "Content_Meditation", "BeginnersList"),
    59: ("18", "Content_Meditation", "WithSoundscapes"),
    60: ("18", "Content_Meditation", "InnerPeace"),
    61: ("18", "Content_Meditation", "FocusList"),
    62: ("18", "Content_Meditation", "EmotionsList"),
    63: ("18", "Content_Meditation", "BodyList"),
    64: ("18", "Content_Meditation", "RelationshipList"),
    
    # ========== CONTENT BROWSE - SLEEP (065-079) ==========
    65: ("19", "Content_Sleep", "ByNarrator"),
    66: ("19", "Content_Sleep", "StoryList"),
    67: ("19", "Content_Sleep", "MusicList"),
    68: ("19", "Content_Sleep", "SoundscapesList"),
    69: ("19", "Content_Sleep", "PlaylistsList"),
    70: ("19", "Content_Sleep", "DownloadsEmpty"),
    71: ("19", "Content_Sleep", "StoryDetail"),
    72: ("19", "Content_Sleep", "StoryPlayer"),
    73: ("19", "Content_Sleep", "StoryPlayerOptions"),
    74: ("19", "Content_Sleep", "StoryShareHint"),
    75: ("19", "Content_Sleep", "StoryRating"),
    76: ("19", "Content_Sleep", "StoryComplete"),
    77: ("19", "Content_Sleep", "StoryShareSheet"),
    78: ("19", "Content_Sleep", "ToolsList"),
    79: ("19", "Content_Sleep", "ToolDetail"),
    
    # ========== DISCOVER TAB (080-084) ==========
    80: ("20", "Discover", "MainPage"),
    81: ("20", "Discover", "SearchResults"),
    82: ("20", "Discover", "CategoryBrowse"),
    83: ("20", "Discover", "CollectionView"),
    84: ("20", "Discover", "ShareAchievement"),
    
    # ========== PROFILE - JOURNAL (085-094) ==========
    85: ("21", "Profile_Journal", "EntriesList"),
    86: ("21", "Profile_Journal", "NewEntry"),
    87: ("21", "Profile_Journal", "EntryDetail"),
    88: ("21", "Profile_Journal", "EditEntry"),
    89: ("21", "Profile_Journal", "DeleteConfirm"),
    90: ("22", "Profile_Reflection", "TodayPrompt"),
    91: ("22", "Profile_Reflection", "WriteReflection"),
    92: ("22", "Profile_Reflection", "SavedReflection"),
    93: ("23", "Profile_Wisdom", "DailyQuote"),
    94: ("23", "Profile_Wisdom", "QuoteShare"),
    95: ("23", "Profile_Wisdom", "QuoteShareSheet"),
    
    # ========== PROFILE - STATS & CHECK-INS (096-104) ==========
    96: ("24", "Profile_Stats", "Overview"),
    97: ("24", "Profile_Stats", "StreakDetail"),
    98: ("24", "Profile_Stats", "MindfulMinutes"),
    99: ("25", "Profile_CheckIn", "MoodHistory"),
    100: ("25", "Profile_CheckIn", "GratitudeEmpty"),
    101: ("25", "Profile_CheckIn", "GratitudeEntry"),
    102: ("25", "Profile_CheckIn", "SleepCheckIn"),
    103: ("26", "Profile_Account", "Overview"),
    104: ("26", "Profile_Account", "EditProfile"),
    
    # ========== SETTINGS (105-120) ==========
    105: ("27", "Settings", "SubscriptionInfo"),
    106: ("27", "Settings", "ManageSubscription"),
    107: ("27", "Settings", "RestorePurchases"),
    108: ("27", "Settings", "RestoreSuccess"),
    109: ("28", "Settings", "NotificationsList"),
    110: ("28", "Settings", "NotificationsDetail"),
    111: ("28", "Settings", "ReminderEdit"),
    112: ("28", "Settings", "BedtimeReminder"),
    113: ("29", "Settings", "PrivacyOptions"),
    114: ("29", "Settings", "DataExport"),
    115: ("29", "Settings", "HealthAccess"),
    116: ("30", "Settings", "LanguageSelect"),
    117: ("30", "Settings", "HelpCenter"),
    118: ("30", "Settings", "About"),
    119: ("30", "Settings", "Logout"),
    120: ("30", "Settings", "MainPage"),
}

def classify():
    """执行分类"""
    count = 0
    for i in range(1, 121):
        src = os.path.join(DOWNLOADS, f"Screen_{i:03d}.png")
        if not os.path.exists(src):
            print(f"[WARN] Not found: {src}")
            continue
        
        if i in CLASSIFICATION:
            phase_num, phase_name, step_desc = CLASSIFICATION[i]
            new_name = f"{phase_num}_{phase_name}_{step_desc}.png"
        else:
            # 未分类的保持原名
            new_name = f"99_Uncategorized_{i:03d}.png"
        
        dst = os.path.join(SCREENS, new_name)
        
        # 处理重名
        if os.path.exists(dst):
            base, ext = os.path.splitext(new_name)
            j = 2
            while os.path.exists(os.path.join(SCREENS, f"{base}_{j}{ext}")):
                j += 1
            new_name = f"{base}_{j}{ext}"
            dst = os.path.join(SCREENS, new_name)
        
        shutil.copy2(src, dst)
        count += 1
        print(f"[OK] {i:03d} -> {new_name}")
    
    print(f"\nDone! {count} screenshots classified")
    print(f"Output: {SCREENS}")

if __name__ == "__main__":
    classify()



import os
import shutil

PROJECT_PATH = r"C:\Users\WIN\Desktop\Cursor Project\PM_Screenshot_Tool\projects\Calm_Analysis"
DOWNLOADS = os.path.join(PROJECT_PATH, "Downloads")
SCREENS = os.path.join(PROJECT_PATH, "screens")

# 清空并重建screens目录
if os.path.exists(SCREENS):
    shutil.rmtree(SCREENS)
os.makedirs(SCREENS)

# 精细分类映射 - 每张截图都经过审核
# 格式: 原始编号 -> (阶段编号, 阶段名, 步骤描述)
CLASSIFICATION = {
    # ========== ONBOARDING FLOW (001-015) ==========
    1: ("01", "Launch", "BreathingGuide"),           # take a deep breath
    2: ("02", "Permission", "Notification"),          # 通知权限
    3: ("02", "Permission", "ATT"),                   # 追踪权限
    4: ("03", "Onboarding", "GoalSelection"),         # What brings you to Calm
    5: ("04", "SignUp", "Entry"),                     # 注册入口
    6: ("04", "SignUp", "Form"),                      # 注册表单填写
    7: ("05", "Paywall", "Main"),                     # 付费墙主页
    8: ("05", "Paywall", "AppStoreConfirm"),          # App Store确认
    9: ("05", "Paywall", "PurchaseSuccess"),          # 购买成功
    10: ("05", "Paywall", "PremiumActivated"),        # Premium激活
    11: ("03", "Onboarding", "Attribution"),          # 渠道来源问卷
    
    # ========== REFERRAL (012-015) ==========
    12: ("06", "Referral", "PopupHome"),              # 推荐弹窗
    13: ("06", "Referral", "MainPage"),               # 推荐计划主页
    14: ("06", "Referral", "ShareSheet"),             # 分享面板
    15: ("06", "Referral", "ShareSuccess"),           # 分享成功
    
    # ========== HOME & ONBOARDING TASKS (016-020) ==========
    16: ("07", "Home", "TaskGuide"),                  # 首页任务引导
    17: ("08", "Feature_Scenes", "List"),             # 场景列表
    18: ("08", "Feature_Scenes", "TimePicker"),       # 时间选择
    19: ("08", "Feature_Scenes", "Preview"),          # 场景预览
    20: ("08", "Feature_Scenes", "Selected"),         # 场景选中
    
    # ========== DAILY PRACTICE (021) ==========
    21: ("09", "Feature_Daily", "PracticeList"),      # 每日练习列表
    
    # ========== PLAYER (022-031) ==========
    22: ("10", "Player", "Controls"),                 # 播放器控制
    23: ("10", "Player", "AirPlay"),                  # AirPlay
    24: ("10", "Player", "ShareSheet"),               # 分享面板
    25: ("10", "Player", "ShareSuccess"),             # 分享成功
    26: ("11", "Engagement", "RatingRequest"),        # 评分请求
    27: ("11", "Engagement", "RatingConfirm"),        # 评分确认
    28: ("10", "Player", "MoreOptions"),              # 更多选项
    29: ("10", "Player", "SpeedOptions"),             # 播放速度
    30: ("10", "Player", "AudioOptions"),             # 音频选项
    31: ("10", "Player", "SubtitleOptions"),          # 字幕选项
    
    # ========== POST SESSION (032-033) ==========
    32: ("12", "PostSession", "Complete"),            # 完成页
    33: ("12", "PostSession", "ShareSheet"),          # 完成后分享
    
    # ========== REMINDER (034-035) ==========
    34: ("13", "Feature_Reminder", "TimePicker"),     # 提醒时间选择
    35: ("13", "Feature_Reminder", "Setup"),          # 提醒设置
    
    # ========== MOOD CHECK-IN (036-040) ==========
    36: ("14", "Feature_MoodCheckIn", "PreSession"),  # 冥想前检查
    37: ("14", "Feature_MoodCheckIn", "Intro1"),      # 功能介绍1
    38: ("14", "Feature_MoodCheckIn", "Intro2"),      # 功能介绍2
    39: ("14", "Feature_MoodCheckIn", "EmojiSelect"), # 情绪选择
    40: ("14", "Feature_MoodCheckIn", "TagSelect"),   # 标签选择
    
    # ========== PLAYER DETAIL (041-051) ==========
    41: ("10", "Player", "DetailPage"),               # 播放详情页
    42: ("10", "Player", "RatingModal"),              # 推荐弹窗
    43: ("10", "Player", "ShareSheet2"),              # 分享面板
    44: ("15", "Feature_Playlist", "Create"),         # 创建播放列表
    45: ("15", "Feature_Playlist", "AddedSuccess"),   # 添加成功
    46: ("15", "Feature_Playlist", "SelectList"),     # 选择列表
    47: ("16", "Settings", "Sound"),                  # 声音设置
    48: ("17", "Content", "NarratorProfile"),         # 讲述者简介
    49: ("10", "Player", "ShareHint"),                # 分享提示
    50: ("10", "Player", "ShareSheet3"),              # 分享面板
    51: ("10", "Player", "ShareSuccess2"),            # 分享成功
    
    # ========== CONTENT BROWSE - MEDITATION (052-064) ==========
    52: ("18", "Content_Meditation", "CategoryAll"),
    53: ("18", "Content_Meditation", "CategorySleep"),
    54: ("18", "Content_Meditation", "CategoryAnxiety"),
    55: ("18", "Content_Meditation", "Featured"),
    56: ("18", "Content_Meditation", "RecentlyPlayed"),
    57: ("18", "Content_Meditation", "QuickList"),
    58: ("18", "Content_Meditation", "BeginnersList"),
    59: ("18", "Content_Meditation", "WithSoundscapes"),
    60: ("18", "Content_Meditation", "InnerPeace"),
    61: ("18", "Content_Meditation", "FocusList"),
    62: ("18", "Content_Meditation", "EmotionsList"),
    63: ("18", "Content_Meditation", "BodyList"),
    64: ("18", "Content_Meditation", "RelationshipList"),
    
    # ========== CONTENT BROWSE - SLEEP (065-079) ==========
    65: ("19", "Content_Sleep", "ByNarrator"),
    66: ("19", "Content_Sleep", "StoryList"),
    67: ("19", "Content_Sleep", "MusicList"),
    68: ("19", "Content_Sleep", "SoundscapesList"),
    69: ("19", "Content_Sleep", "PlaylistsList"),
    70: ("19", "Content_Sleep", "DownloadsEmpty"),
    71: ("19", "Content_Sleep", "StoryDetail"),
    72: ("19", "Content_Sleep", "StoryPlayer"),
    73: ("19", "Content_Sleep", "StoryPlayerOptions"),
    74: ("19", "Content_Sleep", "StoryShareHint"),
    75: ("19", "Content_Sleep", "StoryRating"),
    76: ("19", "Content_Sleep", "StoryComplete"),
    77: ("19", "Content_Sleep", "StoryShareSheet"),
    78: ("19", "Content_Sleep", "ToolsList"),
    79: ("19", "Content_Sleep", "ToolDetail"),
    
    # ========== DISCOVER TAB (080-084) ==========
    80: ("20", "Discover", "MainPage"),
    81: ("20", "Discover", "SearchResults"),
    82: ("20", "Discover", "CategoryBrowse"),
    83: ("20", "Discover", "CollectionView"),
    84: ("20", "Discover", "ShareAchievement"),
    
    # ========== PROFILE - JOURNAL (085-094) ==========
    85: ("21", "Profile_Journal", "EntriesList"),
    86: ("21", "Profile_Journal", "NewEntry"),
    87: ("21", "Profile_Journal", "EntryDetail"),
    88: ("21", "Profile_Journal", "EditEntry"),
    89: ("21", "Profile_Journal", "DeleteConfirm"),
    90: ("22", "Profile_Reflection", "TodayPrompt"),
    91: ("22", "Profile_Reflection", "WriteReflection"),
    92: ("22", "Profile_Reflection", "SavedReflection"),
    93: ("23", "Profile_Wisdom", "DailyQuote"),
    94: ("23", "Profile_Wisdom", "QuoteShare"),
    95: ("23", "Profile_Wisdom", "QuoteShareSheet"),
    
    # ========== PROFILE - STATS & CHECK-INS (096-104) ==========
    96: ("24", "Profile_Stats", "Overview"),
    97: ("24", "Profile_Stats", "StreakDetail"),
    98: ("24", "Profile_Stats", "MindfulMinutes"),
    99: ("25", "Profile_CheckIn", "MoodHistory"),
    100: ("25", "Profile_CheckIn", "GratitudeEmpty"),
    101: ("25", "Profile_CheckIn", "GratitudeEntry"),
    102: ("25", "Profile_CheckIn", "SleepCheckIn"),
    103: ("26", "Profile_Account", "Overview"),
    104: ("26", "Profile_Account", "EditProfile"),
    
    # ========== SETTINGS (105-120) ==========
    105: ("27", "Settings", "SubscriptionInfo"),
    106: ("27", "Settings", "ManageSubscription"),
    107: ("27", "Settings", "RestorePurchases"),
    108: ("27", "Settings", "RestoreSuccess"),
    109: ("28", "Settings", "NotificationsList"),
    110: ("28", "Settings", "NotificationsDetail"),
    111: ("28", "Settings", "ReminderEdit"),
    112: ("28", "Settings", "BedtimeReminder"),
    113: ("29", "Settings", "PrivacyOptions"),
    114: ("29", "Settings", "DataExport"),
    115: ("29", "Settings", "HealthAccess"),
    116: ("30", "Settings", "LanguageSelect"),
    117: ("30", "Settings", "HelpCenter"),
    118: ("30", "Settings", "About"),
    119: ("30", "Settings", "Logout"),
    120: ("30", "Settings", "MainPage"),
}

def classify():
    """执行分类"""
    count = 0
    for i in range(1, 121):
        src = os.path.join(DOWNLOADS, f"Screen_{i:03d}.png")
        if not os.path.exists(src):
            print(f"[WARN] Not found: {src}")
            continue
        
        if i in CLASSIFICATION:
            phase_num, phase_name, step_desc = CLASSIFICATION[i]
            new_name = f"{phase_num}_{phase_name}_{step_desc}.png"
        else:
            # 未分类的保持原名
            new_name = f"99_Uncategorized_{i:03d}.png"
        
        dst = os.path.join(SCREENS, new_name)
        
        # 处理重名
        if os.path.exists(dst):
            base, ext = os.path.splitext(new_name)
            j = 2
            while os.path.exists(os.path.join(SCREENS, f"{base}_{j}{ext}")):
                j += 1
            new_name = f"{base}_{j}{ext}"
            dst = os.path.join(SCREENS, new_name)
        
        shutil.copy2(src, dst)
        count += 1
        print(f"[OK] {i:03d} -> {new_name}")
    
    print(f"\nDone! {count} screenshots classified")
    print(f"Output: {SCREENS}")

if __name__ == "__main__":
    classify()

