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
    dict(love="dinosaurs", label="Dinosaur", page="dinosaur-song-for-kids", tags=["dinosaurs", "dinosaursong"]),
    dict(love="unicorns", label="Unicorn", page="unicorn-song-for-kids", tags=["unicorn", "unicornsong"]),
    dict(love="monster trucks", label="Monster Truck", page="monster-truck-song-for-kids", tags=["monstertrucks", "trucksforkids"]),
    dict(love="mermaids", label="Mermaid", page="mermaid-song-for-kids", tags=["mermaid", "mermaidsong"]),
    dict(love="outer space and rockets", label="Space", page="space-song-for-kids", tags=["space", "rockets"]),
    dict(love="princesses", label="Princess", page="princess-song-for-kids", tags=["princess", "princesssong"]),
    dict(love="sharks", label="Shark", page="shark-song-for-kids", tags=["sharks", "sharksong"]),
    dict(love="ballet and dancing", label="Ballet", page="ballet-song-for-kids", tags=["ballet", "tinydancer"]),
    dict(love="trains", label="Train", page="train-song-for-kids", tags=["trains", "choochoo"]),
    dict(love="puppies", label="Puppy", page="puppy-song-for-kids", tags=["puppies", "puppylove"]),
    dict(love="superheroes", label="Superhero", page="superhero-song-for-kids", tags=["superhero", "superherokids"]),
    dict(love="horses", label="Horse", page="horse-song-for-kids", tags=["horses", "ponylove"]),
    dict(love="fire trucks", label="Fire Truck", page="fire-truck-song-for-kids", tags=["firetruck", "firefighterkids"]),
    dict(love="soccer", label="Soccer", page="soccer-song-for-kids", tags=["soccerkids", "littlesoccer"]),
    dict(love="robots", label="Robot", page="robot-song-for-kids", tags=["robots", "robotsong"]),
    dict(love="construction trucks and diggers", label="Construction", page="construction-song-for-kids", tags=["diggers", "constructiontrucks"]),
    dict(love="pirates", label="Pirate", page="pirate-song-for-kids", tags=["pirates", "piratesong"]),
]

# Post captions. One is picked per post, rotating. Placeholders:
# {name} {love} {label} {url}. Captions are written to parents. AI disclosure is
# handled by the platforms' own AI-content labels set at upload (see daily.py).
CAPTIONS = [
    "This one goes out to every {name} who loves {love} 🎶 Want one with YOUR kid's name? Make it in about a minute at shoutoutsong.com (link in bio)",
    "POV: your kid hears their own name in a song about {love} 🤩 This is our example for {name}. Make one for your kid at shoutoutsong.com (link in bio)",
    "Tag a parent of a {name} 👇 A {label_lower} song with their kid's name in it, made in about a minute at shoutoutsong.com",
    "Every kid deserves a song about them. Here's one for {name} ({love} edition) 🎵 Type your kid's name at shoutoutsong.com (link in bio)",
    "Name + what they love = their own song. Today: {name} and {love} 🎶 Try it free at shoutoutsong.com (link in bio)",
]

BASE_HASHTAGS = ["kidssongs", "personalizedsong", "customsong", "kidsmusic", "momlife", "parenting"]

# Video clip length in seconds (vertical short).
CLIP_SECONDS = 30

# Song length requested from the generator (the API clamps it; the clip is cut from it).
SONG_SECONDS = 60
