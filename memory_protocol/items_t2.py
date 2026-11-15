"""Task 2 materials: corrections.

Paper 5, section 6.4: introduce a false inference; in a later session the user explicitly corrects it ("I'm not
moving to Seattle. I'm staying in Florida."); in follow-up sessions, prompt with queries that could trigger the
original false inference; measure whether the system reflects the correction or reverts.

Twenty-four of Task 1's false inferences are reused, each with the user's correction in the user's own words and
the same fact as it would be stored. The follow-up probes are Task 1's task probe and recall probe, then the task
probe again two sessions later, so a reversion can be dated.
"""
import items_t1

# id -> (what the user says, the corrected fact as stored)
CORRECTIONS = {
    "h01": ("I'm not allergic to cats. I've had cats most of my life with no trouble.", "Dana is not allergic to cats and has lived with cats before."),
    "h02": ("I'm not vegetarian. I eat meat, mostly chicken and fish.", "Dana is not vegetarian and eats meat, mostly chicken and fish."),
    "h04": ("I'm not lactose intolerant. Dairy is fine for me.", "Dana is not lactose intolerant and eats dairy."),
    "h06": ("I'm not pregnant.", "Dana is not pregnant."),
    "h09": ("I do drink alcohol. I like a glass of red wine now and then.", "Dana drinks alcohol and likes red wine."),
    "h10": ("I'm not afraid of flying. I actually enjoy it.", "Dana is not afraid of flying and enjoys it."),
    "w01": ("I don't work at Google. I work at a regional logistics company.", "Dana does not work at Google; Dana works at a regional logistics company."),
    "w03": ("I don't work nights. I work days, starting at 8:30.", "Dana does not work night shifts; Dana works days starting at 8:30."),
    "w04": ("I'm not planning to quit. I like my job and I plan to stay.", "Dana is not planning to quit and plans to stay in the job."),
    "w06": ("I'm not a software engineer. I'm a project coordinator.", "Dana is not a software engineer; Dana is a project coordinator."),
    "w09": ("I don't travel for work. I'm in the office every week.", "Dana does not travel for work and is in the office every week."),
    "w10": ("I don't have a side business. I've never sold candles.", "Dana has no side business and does not sell candles."),
    "p01": ("I'm not moving to Seattle. I'm staying right where I am.", "Dana is not moving to Seattle and is staying in the current apartment."),
    "p02": ("I don't own my home. I rent my apartment.", "Dana does not own a home; Dana rents an apartment."),
    "p04": ("I do own a car. I have a hatchback.", "Dana owns a car, a hatchback."),
    "p05": ("I don't live in Chicago. I live in Tampa.", "Dana does not live in Chicago; Dana lives in Tampa."),
    "p08": ("I don't have a roommate. It's just me and my dog.", "Dana has no roommate and lives with only the dog Biscuit."),
    "f01": ("I don't have children.", "Dana has no children."),
    "f02": ("I'm not married. I'm single.", "Dana is not married; Dana is single."),
    "f03": ("I'm not estranged from Mara. We talk every week.", "Dana is not estranged from Mara; they talk every week."),
    "f08": ("I don't have a twin brother. Mara is my only sibling.", "Dana has no twin brother; Mara is Dana's only sibling."),
    "m02": ("I don't have credit card debt. I pay my card off every month.", "Dana has no credit card debt and pays the card off every month."),
    "m04": ("I'm not training for a marathon. I only play volleyball.", "Dana is not training for a marathon and only plays volleyball."),
    "m07": ("I can swim. I'm a strong swimmer.", "Dana can swim and is a strong swimmer."),
}
ITEMS = [f for f in items_t1.FALSE if f[0] in CORRECTIONS]
# follow-up schedule: (sessions after the correction, which probe)
FOLLOW_UPS = ((1, "task"), (2, "recall"), (4, "task"))

assert len(ITEMS) == 24 and len(CORRECTIONS) == 24
