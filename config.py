"""
Central configuration for the Reddit feed pipeline.

All values have sensible defaults and can be overridden via environment
variables, making the project easy to reconfigure without code changes.
A ``.env`` file in the project root is loaded automatically for local runs.
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()  # loads .env from the working directory, if present


# ---------------------------------------------------------------------------
# Output directory for the generated site
# ---------------------------------------------------------------------------
OUTPUT_DIR: str = os.environ.get("OUTPUT_DIR", "site")

# ---------------------------------------------------------------------------
# Subreddits to follow (required — at least one source needed)
#
# Plain list of subreddits not assigned to any group.
# Supply as a JSON array string via env, e.g. '["funny","pics","aww"]'
# ---------------------------------------------------------------------------
_default_subs: list[str] = []
SUBREDDITS: list[str] = json.loads(
    os.environ.get("SUBREDDITS") or json.dumps(_default_subs)
)

# ---------------------------------------------------------------------------
# Subreddit grouping
#
# Map a human-friendly group name to a list of subreddit names.
# These subreddits are fetched automatically — no need to repeat them in
# SUBREDDITS above. Subreddits not in any group get a standalone group.
#
# Supply as a JSON object string via env to override.
#
# Omitted from defaults (low signal for a daily digest):
#   4CHR, announcements, beta
# ---------------------------------------------------------------------------
_default_groups: dict[str, list[str]] = {
    "🤖 AI": [
        "AgentsOfAI",
        "agi",
        "AI_Agents",
        "aiagents",
        "AIAssisted",
        "AiBuilders",
        "ArtificialInteligence",
        "ChatGPT",
        "ChatGPTCoding",
        "ClaudeAI",
        "google_antigravity",
        "AskVibecoders",
        "GeminiAI",
        "OpenAI",
        "mcp",
        "VibeCodeDevs",
        "vibecoding",
        "vibeprinting",
        "learnmachinelearning",
        "MachineLearning"
    ],
    "💻 Programming": [
        "coding",
        "CodingHelp",
        "commandline",
        "computerscience",
        "bioinformatics",
        "cscareerquestionsEU",
        "howdidtheycodeit",
        "learnprogramming",
        "programming",
        "Python",
        "SideProject",
        "n8n"
    ],
    "🔧 Tech": [
        "Android",
        "androidapps",
        "androiddev",
        "androidroot",
        "gadgets",
        "technology",
        "techsupport",
        "tech",
        "Windows11",
        "MacOS",
        "samsung",
        "virtualreality",
        "augmentedreality",
        "automation",
        "futurology",
        "robotics",
        "macapps"
    ],
    "📊 Data": [
        "datascience",
        "dataisbeautiful",
        "charts",
        "computervision",
        "Infographics",
        "MapPorn",
        "visualization"
    ],
    "💼 Business": [
        "AppBusiness",
        "Business_Ideas",
        "careerguidance",
        "consulting",
        "Big4",
        "FluentInFinance",
        "GrowthHacking",
        "indiehackers",
        "kickstarter",
        "roastmystartup",
        "scaleinpublic",
        "startup",
        "Startup_Ideas",
        "startups",
        "TheFounders",
        "workfromhome"
    ],
    "🍕 Italy": [
        "askitaly",
        "Italia",
        "ItaliaCareerAdvice",
        "ItaliaPersonalFinance",
        "italy",
        "ItalyInformatica",
        "marche",
        "Pesaro",
        "piemonte",
        "torino",
        "TrekkingItaly",
        "xxitaly",
        "xyitaly",
        "ViaggiITA"
    ],
    "🇪🇺 Europe": [
        "budapest",
        "belgium",
        "europe",
        "france",
        "helsinki",
        "ireland",
        "Joensuu",
        "Tampere",
        "Finland",
        "KULeuven",
        "uErasmus",
        "EMJM",
        "Erasmus",
        "ErasmusMundus",
        "IWantOut"
    ],
    "🔬 Science & Academia": [
        "askscience",
        "AskEngineers",
        "AskSocialScience",
        "Anthropology",
        "academia",
        "AcademicPsychology",
        "gradadmissions",
        "PhD",
        "PhDAdmissions",
        "PhdProductivity",
        "research",
        "science"
    ],
    "🧠 Psychology": [
        "askpsychology",
        "consciousness",
        "Neuropsychology",
        "psychology",
        "psychologyresearch",
        "Meditation",
        "meditationpapers",
        "Mindfulness",
        "TheMindIlluminated",
        "ZenHabits",
        "egodeath",
        "Heavymind",
        "Jung",
        "cogsci"
    ],
    "⛪ Philosophy & Religion": [
        "askphilosophy",
        "Catholicism",
        "Christianity",
        "DebateReligion",
        "Ethics",
        "islam",
        "Israel",
        "Jewish",
        "Judaism",
        "OptimisticNihilism",
        "philosophy",
        "PhilosophyMemes",
        "Stoicism",
        "OptimistsUnite"
    ],
    "🌱 Life Improvement": [
        "Adulting",
        "Advice",
        "awesomelife",
        "Biohackers",
        "daddit",
        "declutter",
        "digitalminimalism",
        "getdisciplined",
        "GetMotivated",
        "howtonotgiveafuck",
        "Journaling",
        "LifeAdvice",
        "lifehacks",
        "LifeProTips",
        "minimalism",
        "minimalist",
        "NonZeroDay",
        "productivity",
        "ProductivityApps",
        "QuantifiedSelf",
        "selfhelp",
        "selfimprovement",
        "simpleliving",
        "SlowLiving",
        "longevity",
        "self",
        "relationship_advice",
        "PlannerAddicts"
    ],
    "🏃 Health": [
        "EatCheapAndHealthy",
        "Frugal",
        "personalfinance",
        "MealPrepSunday",
        "nutrition",
        "Supplements",
        "Fitness",
        "walking",
        "yoga",
        "HealthyFood",
        "MobilityTraining"
    ],
    "🎮 Gaming": [
        "gamedev",
        "GameDevelopment",
        "gamedesign",
        "MobileGameDev",
        "MobileGaming",
        "IndieGaming",
        "playmygame",
        "PiratedGames",
        "NintendoSwitch2",
        "roguelites",
        "Games",
        "gaming",
        "hearthstone",
        "CompetitiveHS",
        "magicTCG",
        "mtg",
        "EDH",
        "modthespire",
        "slaythespire",
        "SpiralWarrior"
    ],
    "🍿 Movies & TV": [
        "Cinema",
        "CinemaeTVItalia",
        "cinemaIT",
        "classicfilms",
        "Documentaries",
        "ForeignMovies",
        "iwatchedanoldmovie",
        "Letterboxd",
        "LetterboxdTopFour",
        "moviecritic",
        "MovieDetails",
        "movieleaks",
        "MoviePosterPorn",
        "movies",
        "MovieSuggestions",
        "netflix",
        "NetflixBestOf",
        "television",
        "betterCallSaul",
        "rickandmorty"
    ],
    "📚 Books & Reading": [
        "books",
        "booksuggestions",
        "Libri",
        "libgen",
        "Annas_Archive",
        "ObsidianMD",
        "StoryGraph"
    ],
    "🎧 Music": [
        "AlanParsonsProject",
        "Alternativerock",
        "indie_rock",
        "JusticeMusic",
        "LetsTalkMusic",
        "listentothis",
        "Music",
        "playlists",
        "weirdspotifyplaylists"
    ],
    "🎒 Travel": [
        "backpacking",
        "CampingandHiking",
        "digitalnomad",
        "hiking",
        "overlanding",
        "solotravel",
        "travel",
        "TravelHacks",
        "TravelNoPics",
        "WildernessBackpacking",
        "HerOneBag"
    ],
    "🗾 Japan": [
        "japan",
        "japanese",
        "japaneseresources",
        "japanlife",
        "movingtojapan",
        "language_exchange",
        "LearnJapanese",
        "LearnJapaneseNovice",
        "IWantToLearn"
    ],
    "❓ Ask & Discussion": [
        "ask",
        "AskAPriest",
        "AskGirls",
        "AskHistorians",
        "AskMen",
        "AskReddit",
        "AskTheWorld",
        "AskWomen",
        "askwomenadvice",
        "changemyview",
        "DoesAnybodyElse",
        "explainlikeimfive",
        "IAmA",
        "IsItBullshit",
        "NoStupidQuestions",
        "OutOfTheLoop",
        "RandomThoughts",
        "TrueReddit",
        "TwoXChromosomes",
        "unpopularopinion",
        "YouShouldKnow",
        "moraldilemmas",
        "DeepThoughts",
        "Showerthoughts",
        "AMA",
    ],
    "🎉 Fun": [
        "2000sNostalgia",
        "90s",
        "90s_kid",
        "90sand2000sNostalgia",
        "decadeology",
        "GenZ",
        "lewronggeneration",
        "Millennials",
        "nostalgia",
        "3AMThoughts",
        "AmItheAsshole",
        "assholedesign",
        "bestof",
        "BestofRedditorUpdates",
        "educationalgifs",
        "InternetIsBeautiful",
        "mystery",
        "oddlyspecific",
        "oneliners",
        "quotes",
        "savedyouaclick",
        "tifu",
        "UnethicalLifeProTips",
        "Foodforthought",
        "geography",
        "hopeposting",
        "Lightbulb"
    ],
    "🧩 Hobbies & Misc": [
        "15minutefood",
        "cookingforbeginners",
        "capsulewardrobe",
        "femalelivingspace",
        "HomeMaintenance",
        "lefthanded",
        "lefthanders",
        "malefashionadvice",
        "wimmelbilder",
        "woahdude",
        "outside",
        "thatnightfeeling",
        "Anki",
        "Defcon",
        "degoogle",
        "Design",
        "google",
        "GoogleOne",
        "HowToMen",
        "mealtimevideos",
        "MotivationalQuotes",
        "nosurf",
        "unknownvideos",
        "videos",
        "RedditForGrownups",
        "subredditoftheday",
        "trendingsubreddits",
        "tipofmytongue",
        "todayilearned",
        "UpliftingNews",
        "WatchandLearn",
        "whatisthisthing",
        "wikipedia"
    ],
}
SUBREDDIT_GROUPS: dict[str, list[str]] = json.loads(
    os.environ.get("SUBREDDIT_GROUPS") or json.dumps(_default_groups)
)

# ---------------------------------------------------------------------------
# Feed fetching
# ---------------------------------------------------------------------------
# RSS sorting: "hot", "new", "top", "rising"
# "top" is recommended — it lets Reddit rank by score for us, since
# scores are not available in the RSS feed.
FEED_SORT: str = os.environ.get("FEED_SORT", "top")

# How many posts to request (applied to the combined multi-sub feed)
FETCH_LIMIT: int = int(os.environ.get("FETCH_LIMIT", "100"))

# ---------------------------------------------------------------------------
# Filtering thresholds
# ---------------------------------------------------------------------------
# Discard posts younger than this (hours)
MIN_AGE_HOURS: int = int(os.environ.get("MIN_AGE_HOURS", "12"))

# Discard posts older than this (hours) — 168 = 7 days for weekly digest
MAX_AGE_HOURS: int = int(os.environ.get("MAX_AGE_HOURS", "168"))

# ---------------------------------------------------------------------------
# Blocked keywords — posts whose title contains any of these are dropped.
# Supply as a JSON array string via env, e.g. '["crypto","nft"]'
# ---------------------------------------------------------------------------
_default_keywords: list[str] = ["trump"]
BLOCKED_KEYWORDS: list[str] = json.loads(
    os.environ.get("BLOCKED_KEYWORDS", json.dumps(_default_keywords))
)

# Maximum posts shown per group in the final digest
MAX_POSTS_PER_GROUP: int = int(os.environ.get("MAX_POSTS_PER_GROUP", "10"))

# Maximum posts shown per individual subreddit in the final digest
MAX_POSTS_PER_SUBREDDIT: int = int(os.environ.get("MAX_POSTS_PER_SUBREDDIT", "3"))
