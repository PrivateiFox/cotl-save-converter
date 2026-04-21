"""
migrate.py — iOS 1.4.x → Steam 1.5.x (Woolhaven) field migration.

Applies field renames, format conversions, removals, and Woolhaven default
values to bring an iOS 1.4.x save JSON up to the Steam 1.5.x schema.

Migration data extracted by comparing a real game migration (iOS 1.4.12 save
loaded by Steam client 1.5.25, which auto-migrates and writes the .mp file).
"""
import struct
# ── Fields removed during migration ──────────────────────────────────────────

# iOS 1.4.x slot fields with no Woolhaven equivalent.
SLOT_REMOVE = {
    "AppleArcade_DLC_Clothing",  # iOS-exclusive DLC cosmetic IDs
    "AppleFleeceOnboarded",
    "Apple_Arcade_DLC",
    "CURRENT_WEAPON",
    "Cultist_DLC_Clothing",
    "Food",               # derived subset of items; replaced by "1162"
    "GetTargetChoreXP",
    "Heretic_DLC_Clothing",
    "items",              # reformatted as "1162" — see migrate_slot()
    "PLAYER_STARTING_HEALTH",
    "Pilgrim_DLC_Clothing",
    "PlayerDamageDealt",    # renamed → playerDamageDealt (string → float)
    "PlayerDamageReceived", # renamed → playerDamageReceived
    "PleasureEnabled",
    "Sinful_DLC_Clothing",
    "TailorEnabled",
}

# iOS 1.4.x meta fields removed by Woolhaven migration.
META_REMOVE = {"SaveDate"}

# ── Woolhaven default values ──────────────────────────────────────────────────
# Every key here is a new field introduced in Steam 1.5.x (Woolhaven).
# Values are taken from a real game migration of an iOS 1.4.12 save.
#
# "1162" and playerDamage* are special: migrate_slot() sets them from iOS
# data when available; the values here are only used if that data is absent.

SLOT_DEFAULTS: dict = {
    "1162": [],   # item inventory — overridden from iOS "items" when present
    "1395": [666, 99999, 99997, 99998],
    "AnimalID": 0,
    "BaalNeedsRescue": False,
    "BaalRescued": False,
    "BeatenDungeon5": False,
    "BeatenDungeon6": False,
    "BeatenExecutioner": False,
    "BeatenWolf": False,
    "BeatenYngya": False,
    "BerithTalkedWithBop": False,
    "BlacksmithShopFixed": False,
    "BlacksmithSpokeAboutBrokenShop": False,
    "BlizzardEventID": 0,
    "BlizzardMonsterActive": False,
    "BlizzardOfferingRequirements": [],
    "BlizzardOfferingsCompleted": 0,
    "BlizzardOfferingsGiven": None,
    "BlizzardSnowmenGiven": 0,
    "BreakingOutAnimals": [],
    "BringFishermanWoolStarted": False,
    "BroughtFishingRod": False,
    "BuiltFurnace": False,
    "COOP_PLAYER_FIRE_HEARTS": 0.0,
    "COOP_PLAYER_ICE_HEARTS": 0.0,
    "CanShowExecutionerRoom1": False,
    "CanShowExecutionerRoom2": False,
    "ChosenChildLeftInTheMidasCave": False,
    "ChosenChildMeditationQuestDay": 0,
    "CollectedLightningShards": False,
    "CollectedRotstone": False,
    "CollectedYewMutated": False,
    "CompletedBlacksmithJobBoard": False,
    "CompletedBlizzardSecret": False,
    "CompletedDecoJobBoard": False,
    "CompletedFlockadeJobBoard": False,
    "CompletedGraveyardJobBoard": False,
    "CompletedInfectedNPCQuest": False,
    "CompletedMidasFollowerQuest": False,
    "CompletedOfferingThisBlizzard": False,
    "CompletedRanchingJobBoard": False,
    "CompletedTarotJobBoard": False,
    "CompletedYngyaFightIntro": False,
    "CultLeader5_LastRun": -1,
    "CultLeader5_StoryPosition": -1,
    "CultLeader6_LastRun": -1,
    "CultLeader6_StoryPosition": -1,
    "CurrentDLCDungeonID": -1,
    "CurrentDLCFoxEncounter": 0,
    "CurrentDLCNodeType": 0,
    "CurrentSeason": 0,
    "CurrentWeatherEvent": 0,
    "DLCCurrentUpgradeTreeTier": 0,
    "DLCDungeon5MiniBossIndex": 0,
    "DLCDungeon6MiniBossIndex": 0,
    "DLCDungeonNodeCurrent": -1,
    "DLCDungeonNodesCompleted": [],
    "DLCKey_1": 0,
    "DLCKey_2": 0,
    "DLCKey_3": 0,
    "DLCUpgradeTreeSnowIncrement": 0,
    "DaySinseLastMutatedFollower": 0,
    "DecoShopFixed": False,
    "DecoSpokeAboutBrokenShop": False,
    "DeliveredCharybisLetter": False,
    "DepositFinalFollowerNPC": False,
    "DepositFollowerTargetTraits": [],
    "DepositedFollowerRewardsClaimed": 0,
    "DepositedFollowers": [],
    "DepositedWitnessEyesForRelics": -1,
    "DiedToWolfBoss": False,
    "DiedToYngyaBoss": False,
    "DisableBlizzard1": False,
    "DisableBlizzard2": False,
    "DisableSaving": False,
    "DisableYngyaShrine": False,
    "DisoveredAnimals": [],
    "Doctrine_Winter_Level": 0,
    "Doctrine_Winter_XP": 0.0,
    "DragonEggsCollected": 0,
    "DragonIntrod": False,
    "Dungeon5Harder": False,
    "Dungeon5_Layer": 1,
    "Dungeon6Harder": False,
    "Dungeon6_Layer": 1,
    "DungeonRancherSpecialEncountered": False,
    "EnabledDLCMapHeart": False,
    "EncounteredBaseExpansionNPC": False,
    "EncounteredDungeonRancherCount": 0,
    "EncounteredIcegoreRoom": False,
    "EncounteredSabnock": False,
    "ExecutionerDamned": False,
    "ExecutionerDefeated": False,
    "ExecutionerFindNoteInSilkCradle": False,
    "ExecutionerFollowerNoteGiverID": 0,
    "ExecutionerGivenWeaponFragment": False,
    "ExecutionerInWoolhavenDay": -1,
    "ExecutionerPardoned": False,
    "ExecutionerPardonedDay": -1,
    "ExecutionerPurchases": 0,
    "ExecutionerReceivedMidasHelp": False,
    "ExecutionerReceivedPlimbosHelp": False,
    "ExecutionerRoom1Encountered": False,
    "ExecutionerRoom2Encountered": False,
    "ExecutionerRoomRequiresRevealing": False,
    "ExecutionerRoomRevealed": False,
    "ExecutionerRoomRevealedThisRun": False,
    "ExecutionerRoomUnlocked": False,
    "ExecutionerSpokenToMidas": False,
    "ExecutionerSpokenToPlimbo": False,
    "ExecutionerWoolhavenExecuted": False,
    "ExecutionerWoolhavenSaved": False,
    "FinalDLCMap": False,
    "FindBrokenHammerWeapon": False,
    "FirstDungeon6RescueRoom": False,
    "FirstRotFollowerAilmentAvoided": False,
    "FishCaughtInsideWhaleToday": 0,
    "FishermanDLCSpecialEncountered": False,
    "FishermanGaveWoolAmount": 0,
    "FishermanWinterConvo": False,
    "FlockadeBlacksmithWon": False,
    "FlockadeBlacksmithWoolWon": 0,
    "FlockadeDecoWon": False,
    "FlockadeDecoWoolWon": 0,
    "FlockadeFirstGameOpponentStarts": True,
    "FlockadeFlockadeWon": False,
    "FlockadeFlockadeWoolWon": 0,
    "FlockadeGraveyardWon": False,
    "FlockadeGraveyardWoolWon": 0,
    "FlockadePlayed": False,
    "FlockadeRancherWon": False,
    "FlockadeRancherWoolWon": 0,
    "FlockadeShepherdsTutorialShown": False,
    "FlockadeShopFixed": False,
    "FlockadeSpokeAboutBrokenShop": False,
    "FlockadeTarotWon": False,
    "FlockadeTarotWoolWon": 0,
    "FlockadeTutorialShown": False,
    "FollowerOnboardedAutumnComing": False,
    "FollowerOnboardedBlizzard": False,
    "FollowerOnboardedFreezing": False,
    "FollowerOnboardedOverheating": False,
    "FollowerOnboardedRanchChoppingBlock": False,
    "FollowerOnboardedTyphoon": False,
    "FollowerOnboardedWinterAlmostHere": False,
    "FollowerOnboardedWinterComing": False,
    "FollowerOnboardedWinterHere": False,
    "FollowerOnboardedWoolyShack": False,
    "FollowersTrappedInToxicWaste": 0,
    "Followers_LeftInTheDungeon_IDs": [],
    "Followers_TraitManipulating_IDs": [],
    "FollowingPlayerAnimals": [None, None],
    "ForceDragonRoom": False,
    "ForceHeartRoom": False,
    "ForcePalworldEgg": True,
    "ForceSinRoom": False,
    "ForcingPlayerWeaponDLC": 9999,
    "ForeshadowedWolf": False,
    "FoundHollowKnightWool": False,
    "FoundLegendaryBlunderbuss": False,
    "FoundLegendaryDagger": False,
    "FoundLegendaryGauntlets": False,
    "FoundLegendarySword": False,
    "FrogFollowerCount": 0,
    "FullWoolhavenFlowerPots": [],
    "GaveChosenChildQuest": False,
    "GiveExecutionerFollower": False,
    "GivenBlizzardObjective": False,
    "GivenBrokenHammerWeaponQuest": False,
    "GivenExecutionerFollower": False,
    "GivenMidasFollowerQuest": False,
    "GivenMidasSkull": False,
    "GivenNarayanaFollower": False,
    "GivenUpHeartToWolf": False,
    "GivenUpWolfFood": [],
    "GofernonRotburnProgress": 0,
    "GraveyardShopFixed": False,
    "GraveyardSpokeAboutBrokenShop": False,
    "HadFinalYngyaRoomConvo": False,
    "HaroOnbardedDungeon6": False,
    "HaroOnboardedWinter": False,
    "HasAnimalFeedMeatQuest0Accepted": False,
    "HasAnimalFeedMeatQuest1Accepted": False,
    "HasAnimalFeedMeatQuest2Accepted": False,
    "HasAnimalFeedPoopQuest0Accepted": False,
    "HasAnimalFeedPoopQuest1Accepted": False,
    "HasAnimalFeedPoopQuest2Accepted": False,
    "HasBuildGoodSnowmanQuestAccepted": False,
    "HasFinishedYngyaFlowerBasketQuest": False,
    "HasFurnace": False,
    "HasGivenPedigreeFollower": False,
    "HasLifeToTheIceRitualQuestAccepted": False,
    "HasMidasHiding": False,
    "HasNewFlockadePieces": False,
    "HasPureBloodMatingQuestAccepted": False,
    "HasWalkPoopedAnimalQuestAccepted": False,
    "HasWeatherVane": False,
    "HasWeatherVaneUI": False,
    "HasYngyaConvo": False,
    "HasYngyaFirePitRitualQuestAccepted": False,
    "HasYngyaFlowerBasketQuestAccepted": False,
    "HasYngyaMatingQuestAccepted": False,
    "HintedPieceType": 0,
    "InfectedDudeSpecialEncountered": False,
    "InteractedDLCShrine": False,
    "IsLambGhostRescue": False,
    "IsMiniBoss": True,
    "JobBoardsClaimedQuests": [],
    "KudaaiLegendaryWeaponsResponses": [],
    "LambTownLevel": 0,
    "LambTownWoolGiven": 0,
    "LandConvoProgress": 0,
    "LandPurchased": -1,
    "LandResourcesGiven": 0,
    "LastAnimalLoverPet": 0.0,
    "LastAnimalToStarveDay": -1,
    "LastDayUsedFlockadeHint": -1,
    "LastDungeonSeeds": [],
    "LastIceSculptureBuild": 0.0,
    "LastRanchRitualHarvest": -3.4028234663852886e+38,
    "LastRanchRitualMeat": -3.4028234663852886e+38,
    "LastSimpleGuardianPatternShot": -3.4028234663852886e+38,
    "LastWarmthRitualDeclared": -3.4028234663852886e+38,
    "LeftBopAtTailor": False,
    "LegendaryAxeCustomName": None,
    "LegendaryAxeHinted": False,
    "LegendaryBlunderbussCustomName": None,
    "LegendaryBlunderbussHinted": False,
    "LegendaryBlunderbussPlimboEaterEggTalked": False,
    "LegendaryChainCustomName": None,
    "LegendaryDaggerCustomName": None,
    "LegendaryDaggerHinted": False,
    "LegendaryGauntletCustomName": None,
    "LegendaryGauntletsHinted": False,
    "LegendaryHammerCustomName": None,
    "LegendarySwordCustomName": None,
    "LegendarySwordHinted": False,
    "LegendaryWeaponsJobBoardCompleted": [],
    "LegendaryWeaponsUnlockOrder": [],
    "LongNightActive": False,
    "LostSoulsBark": 0,
    "MAJOR_DLC": False,
    "MajorDLCCachedBaseStructures": [],
    "MapLockCountToUnlock": -1,
    "MidasFollowerInfo": None,
    "MidasHiddenDay": -1,
    "MidasStolenGold": [],
    "MonchMamaSpecialEncountered": False,
    "MysticKeeperBeatenYngya": False,
    "NIL_1312": None,
    "NIL_1313": None,
    "NIL_437": None,
    "NIL_438": None,
    "NPCGhostBlacksmithRescued": False,
    "NPCGhostDecoRescued": False,
    "NPCGhostFlockadeRescued": False,
    "NPCGhostGeneric10Rescued": False,
    "NPCGhostGeneric11Rescued": False,
    "NPCGhostGeneric7Rescued": False,
    "NPCGhostGeneric8Rescued": False,
    "NPCGhostGeneric9Rescued": False,
    "NPCGhostGraveyardRescued": False,
    "NPCGhostRancherRescued": False,
    "NPCGhostTarotRescued": False,
    "NPCRescueRoomsCompleted": 0,
    "NPCsRescued": -1,
    "NextPhaseIsWeatherEvent": False,
    "NextWinterServerity": 0,
    "OnboardedAddFuelToFurnace": False,
    "OnboardedBaseExpansion": False,
    "OnboardedBlacksmithJobBoard": False,
    "OnboardedBlizzards": False,
    "OnboardedDLCBuildMenu": False,
    "OnboardedDLCEntrance": False,
    "OnboardedDecoJobBoard": False,
    "OnboardedDepositFollowerNPC": False,
    "OnboardedDungeon6": False,
    "OnboardedFindLostSouls": False,
    "OnboardedFlockadeJobBoard": False,
    "OnboardedGraveyardJobBoard": False,
    "OnboardedIntroYngyaShrine": False,
    "OnboardedLambGhostNPCs": False,
    "OnboardedLambTown": False,
    "OnboardedLambTownGhost10": False,
    "OnboardedLambTownGhost7": False,
    "OnboardedLambTownGhost8": False,
    "OnboardedLambTownGhost9": False,
    "OnboardedLegendaryWeapons": False,
    "OnboardedLightningShardDungeon": False,
    "OnboardedLongNights": False,
    "OnboardedMutationRoom": False,
    "OnboardedRanching": False,
    "OnboardedRanchingJobBoard": False,
    "OnboardedRanchingWolves": False,
    "OnboardedRotHelobFollowers": False,
    "OnboardedRotRoom": False,
    "OnboardedRotstone": False,
    "OnboardedRotstoneDungeon": False,
    "OnboardedSeasons": False,
    "OnboardedSnowedUnder": False,
    "OnboardedTarotJobBoard": False,
    "OnboardedWitheredCrops": False,
    "OnboardedWolf": False,
    "OnboardedWool": False,
    "OnboardedYewCursedDungeon": False,
    "OnboardedYngyaAwoken": False,
    "PLAYER_FIRE_HEARTS": 0.0,
    "PLAYER_ICE_HEARTS": 0.0,
    "PalworldEggSkinsGiven": [],
    "PalworldEggsCollected": 0,
    "PalworldSkinsGivenLocations": [],
    "PlayedFinalYngyaConvo": False,
    "PlayedPostYngyaSequence": False,
    "PlayerFoundPieces": [0, 100, 200, 203, 3, 103, 202, 102, 2],
    "PlimboRejectedRotEye": False,
    "PreviousRelic": 0,
    "PreviousSeason": 0,
    "PuzzleRoomsCompleted": 0,
    "RancherOnboardedHolyYew": False,
    "RancherOnboardedLightningShards": False,
    "RancherShopFixed": False,
    "RancherSpokeAboutBrokenShop": False,
    "RanchingAnimalsAdded": 0,
    "RatauIntroWoolhaven": False,
    "RatauStaffQuestAliveDead": False,
    "RatauStaffQuestGameConvoPlayed": False,
    "RatauStaffQuestWonGame": False,
    "RatooNeedsRescue": False,
    "RatooRescued": False,
    "ReapedSouls": [],
    "RecruitedRotFollower": False,
    "RefinedElectrifiedRotstone": False,
    "RefinedResourcesSpecialEncountered": False,
    "RemoveBlizzardsBeforeTimestamp": 0.0,
    "RepairedLegendaryAxe": False,
    "RepairedLegendaryBlunderbuss": False,
    "RepairedLegendaryChains": False,
    "RepairedLegendaryDagger": False,
    "RepairedLegendaryGauntlet": False,
    "RepairedLegendaryHammer": False,
    "RepairedLegendarySword": False,
    "RequiresBlizzardOnboarded": False,
    "RequiresSnowedUnderOnboarded": False,
    "RequiresWolvesOnboarded": False,
    "RevealDLCDungeonNode": False,
    "RevealedBaseYngyaShrine": False,
    "RevealedDLCMapDoor": False,
    "RevealedDLCMapHeart": False,
    "RevealedPostDLC": False,
    "RevealedPostGameDungeon5": False,
    "RevealedPostGameDungeon6": False,
    "RevealedWolfNode": False,
    "RoomVariant": 0,
    "RuinedGraveyards": [],
    "STATS_AnimalSacrifices": 0,
    "SacrificeTableInventory": [],
    "SeasonSpecialEventTriggeredDay": -1,
    "SeasonTimestamp": 0,
    "SeasonsActive": False,
    "ShopsBuilt": [],
    "ShowCultWarmth": False,
    "ShowIcegoreRoom": False,
    "ShowMidasKilling": False,
    "ShowSpecialDungeonRancherRoom": False,
    "ShowSpecialFishermanDLCRoom": False,
    "ShowSpecialInfectedDudeRoom": False,
    "ShowSpecialMonchMamaRoom": False,
    "ShowSpecialRefinedResourcesRoom": False,
    "ShowSpecialStelleRoom": False,
    "ShrineGhostJuice": 0,
    "SnowmenCreated": 0,
    "SpokeToYngyaOnMountainTop": False,
    "SpokenToChemachRot": False,
    "SpokenToChemachWinter": False,
    "SpokenToClauneckRot": False,
    "SpokenToClauneckWinter": False,
    "SpokenToHaroD6": False,
    "SpokenToKudaiiRot": False,
    "SpokenToKudaiiWinter": False,
    "SpokenToMysticKeeperWinter": False,
    "SpokenToPlimboBlunderbuss": False,
    "SpokenToPlimboWinter": False,
    "SpokenToRatauWinter": False,
    "StelleSpecialEncountered": False,
    "StripperGaveOutfit": False,
    "TalkedToInfectedNPC": False,
    "TarotShopFixed": False,
    "TarotSpokeAboutBrokenShop": False,
    "Temperature": 50.0,
    "TempleUnlockedBorder5": False,
    "TempleUnlockedBorder6": False,
    "TimeSinceLastAflamedFollower": 0.0,
    "TimeSinceLastAflamedStructure": 0.0,
    "TimeSinceLastFollowerBump": -1.0,
    "TimeSinceLastLightingStrikedFollower": 0.0,
    "TimeSinceLastLightingStrikedStructure": 0.0,
    "TimeSinceLastMissionaryFollowerEncounter": -1.0,
    "TimeSinceLastMurderedFollowerFromFollower": -1.0,
    "TimeSinceLastSnowPileSpawned": -1.0,
    "TimeSinceLastSnowedUnderStructure": 0.0,
    "TimeSinceLastWolf": 0.0,
    "TimeSinceMidasStoleGold": -1.0,
    "TookBopToTailor": False,
    "TotalShrineGhostJuice": 0,
    "TwitchSettings": {
        "NIL_0": None,
        "HelpHinderEnabled": True,
        "HelpHinderFrequency": 20.0,
        "TotemEnabled": True,
        "FollowerNamesEnabled": True,
        "TwitchMessagesEnabled": True,
    },
    "Twitch_Drop_16": False,
    "Twitch_Drop_17": False,
    "Twitch_Drop_18": False,
    "Twitch_Drop_19": False,
    "Twitch_Drop_20": False,
    "UpgradeTreeMenuDLCAlert": False,
    "WarmthBarCount": 0.0,
    "WeatherEventDurationTime": -1.0,
    "WeatherEventID": 0,
    "WeatherEventOverTime": -1.0,
    "WeatherEventTriggeredDay": -1,
    "WinterDoctrineEnabled": False,
    "WinterLoopEnabled": True,
    "WinterLoopModifiedDay": 0,
    "WinterMaxSeverity": False,
    "WinterModeActive": False,
    "WinterServerity": 0,
    "WintersOccured": 0,
    "WoolhavenDecorationCouunt": 0,
    "WoolhavenFlowerPots": [],
    "WoolhavenSkinsPurchased": 0,
    "WoolhavenStructures": [],
    "YngyaHeartRoomEncounters": 0,
    "YngyaMiscConvoIndex": 0,
    "YngyaOffering": 0,
    "YngyaRotOfferingsReceived": 0,
    "bestFriendAnimal": None,
    "bestFriendAnimalAdoration": 0.0,
    "bestFriendAnimalLevel": 0,
    "blizzardEndTimeInCurrentSeason": -1.0,
    "blizzardEndTimeInCurrentSeason2": -1.0,
    "blizzardTimeInCurrentSeason": -1.0,
    "blizzardTimeInCurrentSeason2": -1.0,
    "clickedDLCAd": False,
    "playerDamageDealt": 0.0,    # fallback; override from iOS "PlayerDamageDealt" if present
    "playerDamageReceived": 0.0,  # fallback; override from iOS "PlayerDamageReceived" if present
}

META_DEFAULTS: dict = {
    "ActivatedMajorDLC": False,
    "DLCPercentageCompleted": 3,
    "ExecutionerBeaten": False,
    "LambGhostsCount": 0,
    "RottingFollowerCount": 0,
    "WinterCount": 0,
    "WolfBeaten": False,
    "YngyaBeaten": False,
}


# ── Migration helpers ─────────────────────────────────────────────────────────

def _items_to_1162(items: list) -> list:
    """Convert iOS inventory list to Woolhaven "1162" tuple format.

    iOS:       [{"type": T, "quantity": Q, "QuantityReserved": R, ...}, ...]
    Woolhaven: [[T, Q, R], ...]
    """
    return [
        [item["type"], item["quantity"], item.get("QuantityReserved", 0)]
        for item in items
    ]


def _item_selector_to_tuples(categories: list) -> list:
    """Convert iOS ItemSelectorCategories dicts to Woolhaven positional format.

    iOS:       [{"Key": K, "TrackedItems": [...], "MostRecentItem": N}, ...]
    Woolhaven: [[K, [...], N], ...]
    """
    return [
        [cat["Key"], cat["TrackedItems"], cat["MostRecentItem"]]
        for cat in categories
    ]


def _coerce_float32(obj: object) -> object:
    """Recursively convert all floats to float32 precision.

    iOS saves are JSON, so floats are Python float64.  The C# COTL save struct
    uses float32 for all float fields.  The game coerces every float to float32
    when writing .mp; we do the same so the binary output matches exactly.
    """
    if isinstance(obj, float):
        return struct.unpack(">f", struct.pack(">f", obj))[0]
    if isinstance(obj, list):
        return [_coerce_float32(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _coerce_float32(v) for k, v in obj.items()}
    return obj


# ── Migration functions ───────────────────────────────────────────────────────

def migrate_slot(data: dict) -> dict:
    """Apply Woolhaven migration to an iOS 1.4.x slot save dict.

    Returns a new dict suitable for passing to mp_format.write_mp().
    """
    result = dict(data)

    # Transform item inventory format: "items" → "1162"
    if "items" in result:
        result["1162"] = _items_to_1162(result["items"])

    # Convert ItemSelectorCategories: dicts → positional tuples
    if "ItemSelectorCategories" in result and isinstance(result["ItemSelectorCategories"], list):
        cats = result["ItemSelectorCategories"]
        if cats and isinstance(cats[0], dict):
            result["ItemSelectorCategories"] = _item_selector_to_tuples(cats)

    # Rename damage stats (iOS: camelCase strings → Woolhaven: lowercase float)
    if "PlayerDamageDealt" in result:
        val = result["PlayerDamageDealt"]
        if isinstance(val, str):
            val = float("inf") if val == "Infinity" else float(val)
        result["playerDamageDealt"] = val

    if "PlayerDamageReceived" in result:
        result["playerDamageReceived"] = float(result["PlayerDamageReceived"])

    # Remove iOS-only fields
    for key in SLOT_REMOVE:
        result.pop(key, None)

    # Add missing Woolhaven fields with defaults
    for key, default in SLOT_DEFAULTS.items():
        if key not in result:
            result[key] = default

    # Coerce all floats to float32 precision — COTL's C# save struct uses float32
    # for all float fields; the game does this implicitly when writing .mp saves.
    return _coerce_float32(result)


def migrate_meta(data: dict) -> dict:
    """Apply Woolhaven migration to an iOS 1.4.x meta save dict.

    Returns a new dict suitable for passing to mp_format.write_mp().
    """
    result = dict(data)

    # Remove iOS-only fields
    for key in META_REMOVE:
        result.pop(key, None)

    # Add missing Woolhaven fields with defaults
    for key, default in META_DEFAULTS.items():
        if key not in result:
            result[key] = default

    return result


def migrate_ios(data: dict) -> dict:
    """Apply Woolhaven migration to an iOS save dict (auto-detects slot vs meta).

    Uses the same heuristic as mp_format: fewer than 100 fields with "CultName"
    is a meta save; everything else is a slot save.
    """
    if len(data) < 100 and "CultName" in data:
        return migrate_meta(data)
    return migrate_slot(data)
