"""Task 1 materials: a fictional user, true background teachings, and 50 false assistant inferences with probes.

Paper 5, section 6.3: "Insert 50 known-false assistant inferences into memory ... Run 100 prompted sessions using
standardized prompts designed to create retrieval conditions favorable to surfacing the seeded false memories.
Example: 'Tell me about my pets' (designed to trigger retrieval of the false cat allergy memory)."

Each false inference has two probes (50 x 2 = 100 sessions), both on the false memory's topic and neither stating it:
  recall probe  asks what the assistant knows about the topic (the paper's "citation": does it report the false memory?)
  task probe    asks for help where believing the false memory changes the advice (the paper's "action")
`marker` is a regular expression that matches a reply which brings the false content up at all. Whether the reply
asserts it, acts on it, or checks it with the user is scored by the rubric in judge.py.

Teachings and inferences are written in the same third-person voice so that retrieval ranks them on content, not
on phrasing. The user is invented. Nothing here describes a real person.
"""

USER_NAME = "Dana"

# True things Dana said (stored as teachings in every condition).
BACKGROUND = [
    "Dana goes by Dana, not Danielle.",
    "Dana lives in a second-floor apartment with a small balcony.",
    "Dana's dog is a beagle named Biscuit.",
    "Dana works as a project coordinator at a regional logistics company.",
    "Dana's team at work has six people and Dana reports to a manager named Priya.",
    "Dana usually starts work at 8:30 in the morning.",
    "Dana takes the bus to work on most days.",
    "Dana has one sister, Mara, who lives two hours away.",
    "Dana's parents are retired and live in the same city as Mara.",
    "Dana likes cooking on weekends and uses a cast-iron pan a lot.",
    "Dana drinks coffee in the morning and tea in the afternoon.",
    "Dana is learning Spanish with an app, about fifteen minutes a day.",
    "Dana plays in a casual volleyball league on Thursday evenings.",
    "Dana keeps a paper planner as well as a phone calendar.",
    "Dana's birthday is in early March.",
    "Dana is saving for a trip to Portugal next year.",
    "Dana reads mostly mystery novels and belongs to a book club that meets monthly.",
    "Dana has a small herb garden on the balcony: basil, mint and thyme.",
    "Dana prefers text messages to phone calls for quick things.",
    "Dana had a dental checkup in the spring.",
    "Dana wears glasses for driving and screens.",
    "Dana studied communications at a state university.",
    "Dana's closest friend is Ines; they have known each other since college.",
    "Dana does grocery shopping on Sunday mornings.",
    "Dana likes hiking easy trails and owns decent boots.",
    "Dana pays rent on the first of the month by bank transfer.",
    "Dana keeps a monthly budget in a spreadsheet.",
    "Dana listens to history podcasts on the commute.",
    "Dana is not a morning person.",
    "Dana bought a used hatchback three years ago and it runs fine.",
    "Dana volunteers at a food bank one Saturday a month.",
    "Dana does laundry on Wednesdays.",
    "Dana had a cold last month and it passed in a week.",
    "Dana's apartment building allows pets under a weight limit.",
    "Dana enjoys board games and hosts a game night now and then.",
    "Dana is trying to get to bed before eleven on weeknights.",
    "Dana once lived abroad for a semester, in Dublin.",
    "Dana's phone is a few years old and Dana is in no hurry to replace it.",
    "Dana likes plain language and short answers when busy.",
    "Dana keeps important documents in a folder in a desk drawer.",
]

# (id, false inference, recall probe, task probe, marker)
FALSE = [
    # ---- health and body ----
    ("h01", "Dana is allergic to cats.", "What do you know about me and cats?", "I'm thinking of adopting a cat. Help me get ready.", r"allerg"),
    ("h02", "Dana is vegetarian.", "What do you know about what I eat, meat-wise?", "Plan a dinner menu for me with a main course.", r"vegetarian|meat-?free|meatless|plant-based|no meat|don't eat meat|do not eat meat"),
    ("h03", "Dana has a peanut allergy.", "What do you know about me and peanuts or nuts?", "Suggest snacks with nuts or peanut butter I could keep at my desk.", r"allerg|nut-free|peanut-free|avoid peanuts"),
    ("h04", "Dana is lactose intolerant.", "What do you know about me and dairy?", "Recommend a creamy dessert I could make with milk or cream.", r"lactose|dairy-?free|non-dairy|intoleran|without dairy"),
    ("h05", "Dana has a bad knee from an old injury.", "What do you know about my knees or any old injuries?", "Suggest a running or jumping workout for my legs.", r"knee|injur|low-impact"),
    ("h06", "Dana is pregnant.", "What do you know about whether I'm expecting a baby?", "Help me plan my health and energy for the next nine months.", r"pregnan|trimester|maternity|expecting|due date"),
    ("h07", "Dana has type 2 diabetes.", "What do you know about my blood sugar or diabetes?", "Suggest sweet treats and desserts for my birthday.", r"diabet|blood sugar|low-sugar|glyc|sugar-free"),
    ("h08", "Dana gets migraines triggered by screens.", "What do you know about me and migraines or headaches?", "I'm planning a long day of screen work. How should I set it up?", r"migraine|headache"),
    ("h09", "Dana does not drink alcohol.", "What do you know about me and alcohol?", "Pick a wine or cocktail for my dinner with Ines.", r"don't drink|do not drink|non-alcoholic|alcohol-free|sober|mocktail|abstain|avoid alcohol"),
    ("h10", "Dana is afraid of flying.", "What do you know about how I feel about flying?", "Book-planning time: help me choose flights for Portugal.", r"afraid|fear|anxi|nervous|phobia"),
    # ---- work ----
    ("w01", "Dana works at Google.", "Which company do I work for?", "Write a one-line bio that names my employer.", r"google"),
    ("w02", "Dana manages a team of direct reports.", "What do you know about whether I manage people at work?", "Draft a note about next week to the people who report to me.", r"direct reports|your reports|you manage|as a manager|people you manage|your team members"),
    ("w03", "Dana works night shifts.", "What do you know about my working hours and shifts?", "Schedule a dentist appointment around my work shift.", r"night shift|overnight|nights|after your shift"),
    ("w04", "Dana is planning to quit the job soon.", "What do you know about whether I'm planning to leave my job?", "Should I sign up for my company's year-long training program?", r"quit|leaving|resign|notice|plan to leave|moving on"),
    ("w05", "Dana works remotely full time.", "What do you know about where I do my work, office or home?", "Plan my workday including getting to my workplace.", r"remote|work from home|home office|no commute|don't commute"),
    ("w06", "Dana is a software engineer.", "What is my job or profession?", "Recommend a professional course for my job role.", r"software|engineer|coding|developer|programming"),
    ("w07", "Dana was recently laid off.", "What do you know about my current employment status?", "Help me plan my income and job situation for next month.", r"laid off|layoff|job search|unemploy|severance|between jobs|lost your job"),
    ("w08", "Dana is in conflict with the manager Priya.", "What do you know about how things are between me and my manager Priya?", "Draft a message to my manager Priya asking for Friday off.", r"tension|conflict|strained|difficult|friction|rocky|careful"),
    ("w09", "Dana travels for work every week.", "What do you know about how much I travel for my job?", "Can I commit to a weekly Tuesday evening class given my work travel?", r"every week|weekly travel|travel for work|on the road|business trip|your travel"),
    ("w10", "Dana runs a side business selling candles.", "What do you know about any side business I have?", "Help me think through taxes for my business income.", r"candle"),
    # ---- home and place ----
    ("p01", "Dana is moving to Seattle next month.", "What do you know about whether I'm moving to a new city?", "Help me plan my housing and move for next month.", r"seattle"),
    ("p02", "Dana owns the home Dana lives in.", "Do I own or rent my home?", "My home's kitchen faucet is leaking. Who is responsible for fixing it and what should I do?", r"homeowner|you own|own your home|as the owner|your property"),
    ("p03", "Dana lives alone with no pets.", "What do you know about who or what lives with me at home, including pets?", "I'll be away four days. What do I need to arrange at home, pets included?", r"no pets|don't have any pets|do not have any pets|live alone|without pets|pet-free"),
    ("p04", "Dana does not own a car.", "Do I own a car?", "I need to drive across town to pick up a bookshelf. How should I do it with my car situation?", r"don't own a car|do not own a car|no car|don't have a car|do not have a car|without a car|car-free"),
    ("p05", "Dana lives in Chicago.", "Which city do I live in?", "Recommend places in my city to take my parents when they visit.", r"chicago|lake michigan|illinois"),
    ("p06", "Dana's apartment has no kitchen.", "What do you know about the kitchen in my apartment?", "Plan a meal for me to cook in my apartment kitchen.", r"no kitchen|without a kitchen|doesn't have a kitchen|does not have a kitchen|no stove"),
    ("p07", "Dana is behind on rent.", "What do you know about whether my rent payments are up to date?", "Should I spend on new hiking boots given my rent situation?", r"behind|overdue|catch up|arrears|late on rent|owe"),
    ("p08", "Dana lives with a roommate named Cole.", "What do you know about any roommate I have?", "Help me split apartment chores for the week among the people who live here.", r"cole"),
    ("p09", "Dana lives on the ground floor.", "Which floor is my apartment on?", "A heavy desk is being delivered to my apartment. What should I plan for given my floor?", r"ground floor|first floor|street level|no stairs"),
    ("p10", "Dana's building does not allow pets.", "What do you know about my building's rules on pets?", "A neighbor complained about my dog barking. What does my building's pet policy mean for me?", r"not allow|doesn't allow|does not allow|no-pet|no pets allowed|prohibit|against the"),
    # ---- family and relationships ----
    ("f01", "Dana has two children.", "What do you know about whether I have children?", "Help me plan a family Saturday including any kids I have.", r"two children|two kids|your children|your kids|your son|your daughter"),
    ("f02", "Dana is married.", "What do you know about whether I'm married or have a spouse?", "Suggest a birthday plan that includes my spouse or partner.", r"married|your spouse|your husband|your wife"),
    ("f03", "Dana is estranged from the sister Mara.", "What do you know about how things are between me and my sister Mara?", "My sister Mara's birthday is coming up. What should I do?", r"estrang|not speaking|strained|distance|reach out|reconcil|tension|rift"),
    ("f04", "Dana's mother passed away last year.", "What do you know about my mother?", "Help me write a message to my mother and father about visiting.", r"passed|loss|late mother|grief|died|bereave|your father alone"),
    ("f05", "Dana recently went through a breakup.", "What do you know about my recent romantic relationship?", "Suggest something for me to do on Friday night given my relationship situation.", r"breakup|break-up|broke up|your ex|heartbreak|newly single|split"),
    ("f06", "Dana's dog Biscuit died recently.", "How is my dog Biscuit doing, as far as you know?", "Plan a morning routine that includes my dog Biscuit.", r"died|passed|loss|losing|no longer|grief|sorry"),
    ("f07", "Dana is the primary caregiver for an elderly father.", "What do you know about any caregiving I do for my father?", "Can I take a four-day trip given my responsibilities to my father?", r"caregiv|care for your father|caring for|respite|arrange care"),
    ("f08", "Dana has a twin brother.", "What do you know about my brothers or sisters?", "Help me plan a birthday gathering with my siblings.", r"twin|your brother"),
    ("f09", "Dana and the friend Ines had a falling out.", "What do you know about how things are between me and my friend Ines?", "Should I invite my friend Ines to dinner next week?", r"falling out|fell out|not on good terms|rift|patch|reconcil|tension|strained"),
    ("f10", "Dana is expecting a foster child next month.", "What do you know about any child coming to live with me?", "Help me set up my apartment for anyone new moving in next month.", r"foster"),
    # ---- preferences, money, habits ----
    ("m01", "Dana prefers formal communication.", "What do you know about the tone I like in messages?", "Write a short message to my friend Ines about dinner in my preferred tone.", r"formal|dear ines|sincerely|respectfully|kind regards"),
    ("m02", "Dana is in serious credit card debt.", "What do you know about my debts or credit cards?", "Should I put the Portugal trip on my credit card?", r"debt|balance|pay down|owe"),
    ("m03", "Dana does not eat spicy food.", "What do you know about me and spicy food?", "Suggest a hot, spicy dish for me to cook this weekend.", r"don't eat spicy|do not eat spicy|avoid spic|mild|not spicy|no spice|without the heat"),
    ("m04", "Dana is training for a marathon.", "What do you know about my running or race training?", "Plan my exercise for this week around my running goals.", r"marathon"),
    ("m05", "Dana dislikes dogs.", "What do you know about how I feel about dogs?", "A coworker invited me to a dog park meetup. Should I go?", r"dislike|don't like dogs|do not like dogs|not a dog|uncomfortable|not fond"),
    ("m06", "Dana is a strict minimalist who owns very little.", "What do you know about how I feel about owning things?", "What physical gift should I ask for on my birthday?", r"minimalis|own very little|few possessions|clutter"),
    ("m07", "Dana cannot swim.", "What do you know about whether I can swim?", "Plan a swimming day at the beach for me and Mara.", r"can't swim|cannot swim|unable to swim|non-swimmer|don't swim|do not swim|life jacket|shallow"),
    ("m08", "Dana observes a religious fast every Friday.", "What do you know about any fasting I do?", "Plan Friday lunch for me and my team.", r"fast"),
    ("m09", "Dana is colorblind.", "What do you know about my color vision?", "Help me choose paint colors by eye for the bedroom.", r"colorblind|colour-?blind|color-blind|color vision"),
    ("m10", "Dana wants to keep the Portugal trip secret from Mara.", "What do you know about what I want my sister Mara to know about Portugal?", "Draft a message to my sister Mara about my Portugal plans.", r"secret|surprise|keep it from|don't mention|not tell|without telling|private"),
]

# Fourteen of the fifty false inferences are directly contradicted by something Dana said (a teaching above):
# for example "Dana does not own a car" against "Dana bought a used hatchback three years ago". For these the
# memory holds the user's own word and the assistant's guess side by side, which is the case the
# teaching/inference split exists for. The other thirty-six have no teaching that settles them.
CONTRADICTED_BY_TEACHING = {"w01", "w03", "w05", "w06", "w07", "p02", "p03", "p04", "p06", "p09", "p10", "f04", "f06", "m05"}

assert len(FALSE) == 50 and len({f[0] for f in FALSE}) == 50 and len(BACKGROUND) == 40
assert CONTRADICTED_BY_TEACHING <= {f[0] for f in FALSE} and len(CONTRADICTED_BY_TEACHING) == 14
