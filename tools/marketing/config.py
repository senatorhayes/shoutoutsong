"""Settings for the daily example-song job (tools/marketing/daily.py).

Edit these lists freely. The job walks through them in order, one song per run,
and remembers where it left off in state.json.
"""

# Popular US first names, mixed. Order = posting order.
NAMES = [
    "Olivia", "Liam", "Emma", "Noah", "Charlotte", "Oliver", "Amelia", "Theodore",
    "Sophia", "James", "Mia", "Henry", "Isabella", "Lucas", "Ava", "Elijah",
    "Evelyn", "Mateo", "Luna", "Benjamin", "Harper", "Levi", "Ella", "Sebastian",
    "Sofia", "Jack", "Scarlett", "Ezra", "Mila", "Leo", "Aria", "Hudson",
    "Nova", "Owen", "Chloe", "Asher", "Layla", "Grayson", "Ellie", "Ethan",
    "Hazel", "Daniel", "Lily", "Michael", "Gianna", "Samuel", "Violet", "Wyatt",
    "Aurora", "Jackson", "Penelope", "Luca", "Nora", "Alexander", "Zoey", "Mason",
    "Riley", "William", "Emily", "Logan", "Eleanor", "Jacob", "Isla", "Carter",
    "Ivy", "Julian", "Willow", "Jayden", "Grace", "Elias", "Stella", "Maverick",
    "Avery", "Josiah", "Hannah", "Kai", "Lucy", "Gabriel", "Delilah", "David",
    "Emilia", "Lincoln", "Madison", "Jaxon", "Naomi", "Waylon", "Paisley", "Ezekiel",
    "Elena", "Miles", "Leah", "Isaiah", "Kinsley", "Anthony", "Addison", "Theo",
    "Josephine", "Matthew", "Everly", "Aiden", "Camila", "Rowan", "Ruby", "Dylan",
    "Abigail", "Caleb", "Eliana", "Silas", "Quinn", "Adam", "Maya", "Roman",
    "Sadie", "Ryan", "Athena", "Nathan", "Lainey", "Jonah", "Bella", "Max",
]

# What the kid loves. `love` is sent to the song generator, `label` is used in
# titles, `page` is the existing landing page for that theme, `tags` go on posts.
THEMES = [
    dict(love="dinosaurs", label="Dinosaur", page="dinosaur-song-for-kids", tags=["dinosaurs", "dinosaursong"], weight=2,
         scene="friendly baby dinosaurs in a lush green prehistoric valley with volcanoes and ferns"),
    dict(love="unicorns", label="Unicorn", page="unicorn-song-for-kids", tags=["unicorn", "unicornsong"], weight=2,
         scene="a happy unicorn on rainbow hills with fluffy pink clouds"),
    dict(love="monster trucks", label="Monster Truck", page="monster-truck-song-for-kids", tags=["monstertrucks", "trucksforkids"], weight=2,
         scene="a smiling monster truck with big bouncy wheels jumping over dirt hills"),
    dict(love="mermaids", label="Mermaid", page="mermaid-song-for-kids", tags=["mermaid", "mermaidsong"],
         scene="a cheerful mermaid swimming with fish under the sea among coral"),
    dict(love="outer space and rockets", label="Space", page="space-song-for-kids", tags=["space", "rockets"],
         scene="a little rocket ship flying past smiling planets and twinkling stars"),
    dict(love="princesses", label="Princess", page="princess-song-for-kids", tags=["princess", "princesssong"], weight=2,
         scene="a sweet princess with a sparkly crown in front of a pastel castle"),
    dict(love="sharks", label="Shark", page="shark-song-for-kids", tags=["sharks", "sharksong"],
         scene="a friendly smiling baby shark swimming in a bright blue ocean"),
    dict(love="ballet and dancing", label="Ballet", page="ballet-song-for-kids", tags=["ballet", "tinydancer"],
         scene="a little ballerina twirling on a stage with soft spotlights"),
    dict(love="trains", label="Train", page="train-song-for-kids", tags=["trains", "choochoo"],
         scene="a happy little steam train chugging along tracks through green hills"),
    dict(love="puppies and doggies", label="Puppy", page="puppy-song-for-kids", tags=["puppies", "puppylove", "doggies"], weight=2,
         scene="playful puppies chasing a ball in a sunny backyard"),
    dict(love="superheroes", label="Superhero", page="superhero-song-for-kids", tags=["superhero", "superherokids"],
         scene="a little kid superhero in a cape flying over a cartoon city"),
    dict(love="horses", label="Horse", page="horse-song-for-kids", tags=["horses", "ponylove"],
         scene="a happy pony galloping across a sunny farm meadow"),
    dict(love="fire trucks", label="Fire Truck", page="fire-truck-song-for-kids", tags=["firetruck", "firefighterkids"], weight=2,
         scene="a smiling red fire truck with ladder and lights driving through a cartoon town"),
    dict(love="soccer", label="Soccer", page="soccer-song-for-kids", tags=["soccerkids", "littlesoccer"],
         scene="a little kid kicking a soccer ball on a bright green field"),
    dict(love="robots", label="Robot", page="robot-song-for-kids", tags=["robots", "robotsong"],
         scene="a cute friendly robot dancing with blinking lights"),
    dict(love="construction trucks and diggers", label="Construction", page="construction-song-for-kids", tags=["diggers", "constructiontrucks"], weight=2,
         scene="smiling diggers, dump trucks and cranes working on a sunny construction site"),
    dict(love="pirates", label="Pirate", page="pirate-song-for-kids", tags=["pirates", "piratesong"],
         scene="a little pirate ship with a friendly parrot sailing on gentle waves"),
    # Added Nov 2026
    dict(love="race cars", label="Race Car", page="song-with-your-childs-name", tags=["racecars", "carsforkids"], weight=2,
         scene="colorful smiling race cars zooming around a race track"),
    dict(love="airplanes", label="Airplane", page="song-with-your-childs-name", tags=["airplanes", "planesforkids"], weight=2,
         scene="a happy little airplane flying through fluffy clouds in a blue sky"),
    dict(love="farm animals", label="Farm Animals", page="song-with-your-childs-name", tags=["farmanimals", "oldmacdonald"],
         scene="happy cows, pigs, sheep and chickens on a red-barn farm"),
    dict(love="jungle animals", label="Jungle Animals", page="song-with-your-childs-name", tags=["jungleanimals", "zooanimals"],
         scene="a lion, elephant, giraffe and monkey playing in a bright jungle"),
    dict(love="fairies and butterflies", label="Fairy", page="song-with-your-childs-name", tags=["fairies", "butterflies"],
         scene="a tiny fairy flying among butterflies and flowers in a magical garden"),
    dict(love="rainbows", label="Rainbow", page="song-with-your-childs-name", tags=["rainbows", "rainbowsong"],
         scene="a giant smiling rainbow over happy clouds and a sunny sky"),
    dict(love="kittens", label="Kitten", page="song-with-your-childs-name", tags=["kittens", "kittenlove"],
         scene="playful fluffy kittens chasing yarn in a cozy room"),
]

# Holiday themes. During a window, SEASON_SHARE of videos (2 of every 3) use the holiday theme.
# start/end are "MM-DD" (inclusive). Easter's window is computed from the Easter date each year.
SEASON_SHARE = 2 / 3
SEASONS = [
    dict(start="11-15", end="12-25", theme=dict(love="Christmas", label="Christmas", page="christmas-song-for-kids",
         tags=["christmas", "christmassong", "santa"],
         scene="a cozy Christmas scene with a decorated tree, presents, snow and Santa's sleigh")),
    dict(start="12-26", end="01-01", theme=dict(love="New Year's Eve", label="New Year", page="song-with-your-childs-name",
         tags=["newyear", "happynewyear"],
         scene="happy party hats, balloons and gentle fireworks in a night sky")),
    dict(start="02-01", end="02-14", theme=dict(love="Valentine's Day", label="Valentine", page="song-with-your-childs-name",
         tags=["valentinesday", "valentine"],
         scene="floating pink hearts, cute teddy bears and flowers")),
    dict(easter=True, days_before=21, theme=dict(love="Easter", label="Easter", page="song-with-your-childs-name",
         tags=["easter", "easterbunny"],
         scene="a fluffy Easter bunny hopping among colorful painted eggs in a spring meadow")),
    dict(start="10-01", end="10-31", theme=dict(love="Halloween", label="Halloween", page="song-with-your-childs-name",
         tags=["halloween", "halloweenkids"],
         scene="friendly smiling pumpkins, cute little ghosts and a not-scary moonlit night")),
]

# Post captions. One is picked per post, rotating. Placeholders:
# {name} {love} {label} {url}. Captions are written to parents. AI disclosure is
# handled by the platforms' own AI-content labels set at upload (see daily.py).
CAPTIONS = [
    "This one's for every {name} who loves {love} 🎶\n\nImagine your kid hearing THEIR name in a song. Make one in about a minute, link in bio.\n\nFree preview, ready in about a minute.",
    "POV: your kid hears their own name in a song about {love} 🎵\n\nToday's star: {name}. Want one starring your little one? Link in bio.",
    "Know a little {name}? Tag their mom or dad 👇\n\nWe made a {label_lower} song just for them. Make one with your kid's name at ShoutOutSong.com (link in bio).",
    "{label} song for {name} 🎶\n\nEvery kid deserves a song all about them. Type your kid's name and what they love, and hear it free. Link in bio.",
    "Name + what they love = their very own song 🎤\n\nToday: {name} and {love}. Your turn: free preview at ShoutOutSong.com (link in bio).",
]

BASE_HASHTAGS = ["kidssongs", "personalizedsong", "customsong", "kidsmusic", "momlife", "parenting"]

# Added to the end of every social caption, before the hashtags.
CAPTION_ENDING = "Comment your kid's name + what they love and we might make the next one 👇"

# Video clip length in seconds (vertical short).
CLIP_SECONDS = 30

# Song length requested from the generator (the API clamps it; the clip is cut from it).
SONG_SECONDS = 60

# ---------------------------------------------------------------- cartoon clips
# When a theme has fewer than CLIPS_PER_THEME clips in tools/marketing/clips/<theme>/,
# the job makes a new one with an AI video model on fal.ai (needs the FAL_KEY secret),
# saves it, and reuses it in later videos. About $0.35 per 5-second clip.
CLIPS_PER_THEME = 0  # 0 = only use the clips in the folders (made in Midjourney); >0 = top up with AI clips via fal.ai
CLIP_MODEL = "fal-ai/kling-video/v2.6/pro/text-to-video"
CLIP_PROMPT = ("Cute 2D cartoon animation for young children: {subject}, {action}. "
               "Bright cheerful pastel colors, soft rounded shapes, smiling friendly characters, "
               "simple clean background, gentle smooth motion, children's picture-book style. "
               "No text, no letters, no words, no logos.")
CLIP_ACTIONS = [
    "playing happily",
    "dancing and bouncing joyfully",
    "on a fun little adventure with sparkles and floating bubbles",
]
CLIP_NEGATIVE = "text, letters, words, logo, watermark, scary, dark, realistic, photo, blur, distorted, low quality"
