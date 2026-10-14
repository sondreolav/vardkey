"""A local guard against wallet secrets pasted into a free-text field.

Section 2 forbids the app from ever asking for or storing a seed phrase, a
private key, a PIN, a password, or any other wallet secret, and section 15
repeats it for the database. The app has no column for such a value, but the
free-text fields are written exactly as the user typed them, so a secret can
still arrive by accident: a seed phrase copied off a piece of paper, or an
extended private key copied out of a wallet.

This module is the one place that decides whether a piece of text looks like one
of those secrets. It is deliberately:

- **local** — nothing is sent anywhere and there is no network call;
- **silent** — the text is never put into a log, a message, or an exception. The
  caller gets a short label for what was recognised, never the value;
- **narrow** — it matches the few shapes that are unmistakable, so an ordinary
  note is not refused. A false positive blocks a legitimate note, which is worse
  than missing an exotic format.

``find_secret()`` returns a short English label such as ``"a seed phrase"``, or
``None`` when nothing was recognised. ``rejection_message()`` turns that into the
sentence the user sees.

What the guard does **not** catch is written down under ``LIMITATIONS``. The
guard is a safeguard, not a proof: claiming the app can never store a secret
would be a claim it cannot keep.

LIMITATIONS
-----------
- A bare 64-character hexadecimal string is not refused. It is indistinguishable
  from a transaction id or a hash, which are legitimate note content, so
  refusing it would block ordinary use.
- Only the English BIP39 wordlist is used. A phrase in another language, or one
  where a word is misspelled, is not recognised by the word run.
- A secret that is split across several fields, or written in a shape that does
  not match one of the patterns below, is not caught.
- The length limits in ``validation.py`` are the second line of defence: every
  free-text field is bounded, so a secret cannot be stored in an unbounded blob.
"""

import re


# The English BIP39 wordlist, 2048 words, in the order the specification lists
# them (bitcoin/bips, bip-0039/english.txt). A seed phrase is a run of words from
# this list, so membership is what makes the phrase recognisable. The list is
# embedded rather than fetched, because the app is local and makes no network
# call; ``tests/test_secret_guard.py`` checks the list is complete.
BIP39_WORDS = tuple("""
abandon ability able about above absent absorb abstract absurd abuse
access accident account accuse achieve acid acoustic acquire across act
action actor actress actual adapt add addict address adjust admit
adult advance advice aerobic affair afford afraid again age agent
agree ahead aim air airport aisle alarm album alcohol alert
alien all alley allow almost alone alpha already also alter
always amateur amazing among amount amused analyst anchor ancient anger
angle angry animal ankle announce annual another answer antenna antique
anxiety any apart apology appear apple approve april arch arctic
area arena argue arm armed armor army around arrange arrest
arrive arrow art artefact artist artwork ask aspect assault asset
assist assume asthma athlete atom attack attend attitude attract auction
audit august aunt author auto autumn average avocado avoid awake
aware away awesome awful awkward axis baby bachelor bacon badge
bag balance balcony ball bamboo banana banner bar barely bargain
barrel base basic basket battle beach bean beauty because become
beef before begin behave behind believe below belt bench benefit
best betray better between beyond bicycle bid bike bind biology
bird birth bitter black blade blame blanket blast bleak bless
blind blood blossom blouse blue blur blush board boat body
boil bomb bone bonus book boost border boring borrow boss
bottom bounce box boy bracket brain brand brass brave bread
breeze brick bridge brief bright bring brisk broccoli broken bronze
broom brother brown brush bubble buddy budget buffalo build bulb
bulk bullet bundle bunker burden burger burst bus business busy
butter buyer buzz cabbage cabin cable cactus cage cake call
calm camera camp can canal cancel candy cannon canoe canvas
canyon capable capital captain car carbon card cargo carpet carry
cart case cash casino castle casual cat catalog catch category
cattle caught cause caution cave ceiling celery cement census century
cereal certain chair chalk champion change chaos chapter charge chase
chat cheap check cheese chef cherry chest chicken chief child
chimney choice choose chronic chuckle chunk churn cigar cinnamon circle
citizen city civil claim clap clarify claw clay clean clerk
clever click client cliff climb clinic clip clock clog close
cloth cloud clown club clump cluster clutch coach coast coconut
code coffee coil coin collect color column combine come comfort
comic common company concert conduct confirm congress connect consider control
convince cook cool copper copy coral core corn correct cost
cotton couch country couple course cousin cover coyote crack cradle
craft cram crane crash crater crawl crazy cream credit creek
crew cricket crime crisp critic crop cross crouch crowd crucial
cruel cruise crumble crunch crush cry crystal cube culture cup
cupboard curious current curtain curve cushion custom cute cycle dad
damage damp dance danger daring dash daughter dawn day deal
debate debris decade december decide decline decorate decrease deer defense
define defy degree delay deliver demand demise denial dentist deny
depart depend deposit depth deputy derive describe desert design desk
despair destroy detail detect develop device devote diagram dial diamond
diary dice diesel diet differ digital dignity dilemma dinner dinosaur
direct dirt disagree discover disease dish dismiss disorder display distance
divert divide divorce dizzy doctor document dog doll dolphin domain
donate donkey donor door dose double dove draft dragon drama
drastic draw dream dress drift drill drink drip drive drop
drum dry duck dumb dune during dust dutch duty dwarf
dynamic eager eagle early earn earth easily east easy echo
ecology economy edge edit educate effort egg eight either elbow
elder electric elegant element elephant elevator elite else embark embody
embrace emerge emotion employ empower empty enable enact end endless
endorse enemy energy enforce engage engine enhance enjoy enlist enough
enrich enroll ensure enter entire entry envelope episode equal equip
era erase erode erosion error erupt escape essay essence estate
eternal ethics evidence evil evoke evolve exact example excess exchange
excite exclude excuse execute exercise exhaust exhibit exile exist exit
exotic expand expect expire explain expose express extend extra eye
eyebrow fabric face faculty fade faint faith fall false fame
family famous fan fancy fantasy farm fashion fat fatal father
fatigue fault favorite feature february federal fee feed feel female
fence festival fetch fever few fiber fiction field figure file
film filter final find fine finger finish fire firm first
fiscal fish fit fitness fix flag flame flash flat flavor
flee flight flip float flock floor flower fluid flush fly
foam focus fog foil fold follow food foot force forest
forget fork fortune forum forward fossil foster found fox fragile
frame frequent fresh friend fringe frog front frost frown frozen
fruit fuel fun funny furnace fury future gadget gain galaxy
gallery game gap garage garbage garden garlic garment gas gasp
gate gather gauge gaze general genius genre gentle genuine gesture
ghost giant gift giggle ginger giraffe girl give glad glance
glare glass glide glimpse globe gloom glory glove glow glue
goat goddess gold good goose gorilla gospel gossip govern gown
grab grace grain grant grape grass gravity great green grid
grief grit grocery group grow grunt guard guess guide guilt
guitar gun gym habit hair half hammer hamster hand happy
harbor hard harsh harvest hat have hawk hazard head health
heart heavy hedgehog height hello helmet help hen hero hidden
high hill hint hip hire history hobby hockey hold hole
holiday hollow home honey hood hope horn horror horse hospital
host hotel hour hover hub huge human humble humor hundred
hungry hunt hurdle hurry hurt husband hybrid ice icon idea
identify idle ignore ill illegal illness image imitate immense immune
impact impose improve impulse inch include income increase index indicate
indoor industry infant inflict inform inhale inherit initial inject injury
inmate inner innocent input inquiry insane insect inside inspire install
intact interest into invest invite involve iron island isolate issue
item ivory jacket jaguar jar jazz jealous jeans jelly jewel
job join joke journey joy judge juice jump jungle junior
junk just kangaroo keen keep ketchup key kick kid kidney
kind kingdom kiss kit kitchen kite kitten kiwi knee knife
knock know lab label labor ladder lady lake lamp language
laptop large later latin laugh laundry lava law lawn lawsuit
layer lazy leader leaf learn leave lecture left leg legal
legend leisure lemon lend length lens leopard lesson letter level
liar liberty library license life lift light like limb limit
link lion liquid list little live lizard load loan lobster
local lock logic lonely long loop lottery loud lounge love
loyal lucky luggage lumber lunar lunch luxury lyrics machine mad
magic magnet maid mail main major make mammal man manage
mandate mango mansion manual maple marble march margin marine market
marriage mask mass master match material math matrix matter maximum
maze meadow mean measure meat mechanic medal media melody melt
member memory mention menu mercy merge merit merry mesh message
metal method middle midnight milk million mimic mind minimum minor
minute miracle mirror misery miss mistake mix mixed mixture mobile
model modify mom moment monitor monkey monster month moon moral
more morning mosquito mother motion motor mountain mouse move movie
much muffin mule multiply muscle museum mushroom music must mutual
myself mystery myth naive name napkin narrow nasty nation nature
near neck need negative neglect neither nephew nerve nest net
network neutral never news next nice night noble noise nominee
noodle normal north nose notable note nothing notice novel now
nuclear number nurse nut oak obey object oblige obscure observe
obtain obvious occur ocean october odor off offer office often
oil okay old olive olympic omit once one onion online
only open opera opinion oppose option orange orbit orchard order
ordinary organ orient original orphan ostrich other outdoor outer output
outside oval oven over own owner oxygen oyster ozone pact
paddle page pair palace palm panda panel panic panther paper
parade parent park parrot party pass patch path patient patrol
pattern pause pave payment peace peanut pear peasant pelican pen
penalty pencil people pepper perfect permit person pet phone photo
phrase physical piano picnic picture piece pig pigeon pill pilot
pink pioneer pipe pistol pitch pizza place planet plastic plate
play please pledge pluck plug plunge poem poet point polar
pole police pond pony pool popular portion position possible post
potato pottery poverty powder power practice praise predict prefer prepare
present pretty prevent price pride primary print priority prison private
prize problem process produce profit program project promote proof property
prosper protect proud provide public pudding pull pulp pulse pumpkin
punch pupil puppy purchase purity purpose purse push put puzzle
pyramid quality quantum quarter question quick quit quiz quote rabbit
raccoon race rack radar radio rail rain raise rally ramp
ranch random range rapid rare rate rather raven raw razor
ready real reason rebel rebuild recall receive recipe record recycle
reduce reflect reform refuse region regret regular reject relax release
relief rely remain remember remind remove render renew rent reopen
repair repeat replace report require rescue resemble resist resource response
result retire retreat return reunion reveal review reward rhythm rib
ribbon rice rich ride ridge rifle right rigid ring riot
ripple risk ritual rival river road roast robot robust rocket
romance roof rookie room rose rotate rough round route royal
rubber rude rug rule run runway rural sad saddle sadness
safe sail salad salmon salon salt salute same sample sand
satisfy satoshi sauce sausage save say scale scan scare scatter
scene scheme school science scissors scorpion scout scrap screen script
scrub sea search season seat second secret section security seed
seek segment select sell seminar senior sense sentence series service
session settle setup seven shadow shaft shallow share shed shell
sheriff shield shift shine ship shiver shock shoe shoot shop
short shoulder shove shrimp shrug shuffle shy sibling sick side
siege sight sign silent silk silly silver similar simple since
sing siren sister situate six size skate sketch ski skill
skin skirt skull slab slam sleep slender slice slide slight
slim slogan slot slow slush small smart smile smoke smooth
snack snake snap sniff snow soap soccer social sock soda
soft solar soldier solid solution solve someone song soon sorry
sort soul sound soup source south space spare spatial spawn
speak special speed spell spend sphere spice spider spike spin
spirit split spoil sponsor spoon sport spot spray spread spring
spy square squeeze squirrel stable stadium staff stage stairs stamp
stand start state stay steak steel stem step stereo stick
still sting stock stomach stone stool story stove strategy street
strike strong struggle student stuff stumble style subject submit subway
success such sudden suffer sugar suggest suit summer sun sunny
sunset super supply supreme sure surface surge surprise surround survey
suspect sustain swallow swamp swap swarm swear sweet swift swim
swing switch sword symbol symptom syrup system table tackle tag
tail talent talk tank tape target task taste tattoo taxi
teach team tell ten tenant tennis tent term test text
thank that theme then theory there they thing this thought
three thrive throw thumb thunder ticket tide tiger tilt timber
time tiny tip tired tissue title toast tobacco today toddler
toe together toilet token tomato tomorrow tone tongue tonight tool
tooth top topic topple torch tornado tortoise toss total tourist
toward tower town toy track trade traffic tragic train transfer
trap trash travel tray treat tree trend trial tribe trick
trigger trim trip trophy trouble truck true truly trumpet trust
truth try tube tuition tumble tuna tunnel turkey turn turtle
twelve twenty twice twin twist two type typical ugly umbrella
unable unaware uncle uncover under undo unfair unfold unhappy uniform
unique unit universe unknown unlock until unusual unveil update upgrade
uphold upon upper upset urban urge usage use used useful
useless usual utility vacant vacuum vague valid valley valve van
vanish vapor various vast vault vehicle velvet vendor venture venue
verb verify version very vessel veteran viable vibrant vicious victory
video view village vintage violin virtual virus visa visit visual
vital vivid vocal voice void volcano volume vote voyage wage
wagon wait walk wall walnut want warfare warm warrior wash
wasp waste water wave way wealth weapon wear weasel weather
web wedding weekend weird welcome west wet whale what wheat
wheel when where whip whisper wide width wife wild will
win window wine wing wink winner winter wire wisdom wise
wish witness wolf woman wonder wood wool word work world
worry worth wrap wreck wrestle wrist write wrong yard year
yellow you young youth zebra zero zone zoo
""".split())

# The lookup the word run is checked against, built once.
_BIP39_LOOKUP = frozenset(BIP39_WORDS)

# A mnemonic is 12, 15, 18, 21 or 24 words, and every word comes from the list.
# A run of at least 12 words is used as the threshold: a short note that happens
# to use a few of these words is left alone, because a false positive would block
# a legitimate note.
MNEMONIC_MIN_WORDS = 12

# A PEM private-key block names itself.
PEM_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")

# The base58 alphabet, which is what every key-shaped token below is written in.
BASE58 = frozenset("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")

# BIP32 extended private keys, including the SLIP-132 prefixes. An xpub is a
# public key and is not refused; only the private halves are.
EXTENDED_PRIVATE_KEY_PREFIXES = ("xprv", "yprv", "zprv", "tprv", "uprv", "vprv")
EXTENDED_PRIVATE_KEY_MIN_LENGTH = 100

# A WIF private key: 51 characters when it is uncompressed and 52 when it is
# compressed. The leading character says which network and form it is.
WIF_PREFIXES = ("5", "9", "K", "L", "c")
WIF_LENGTHS = (51, 52)

# A BIP38 encrypted private key.
BIP38_PREFIX = "6p"
BIP38_LENGTH = 58

# A token is a run of letters and digits, and a word is a run of letters only.
TOKEN = re.compile(r"[A-Za-z0-9]+")
WORD = re.compile(r"[A-Za-z]+")


def find_secret(text):
    """Return a short label for a wallet secret in the text, or ``None``.

    The label never contains any of the text, so it is safe to put in a message
    or a log. The caller decides what to do with it; ``validation.py`` refuses the
    field and ``auth.py`` refuses the admin username.
    """
    if not isinstance(text, str) or not text:
        return None
    if PEM_PRIVATE_KEY.search(text):
        return "a PEM private key"
    for token in TOKEN.findall(text):
        label = _token_secret(token)
        if label is not None:
            return label
    if _has_mnemonic_run(text):
        return "a seed phrase"
    return None


def rejection_message(field, label):
    """Return the sentence a refused field gets.

    It names the field and the shape that was recognised, says plainly that
    nothing was stored, and tells the user what to do next. It never repeats the
    value itself.
    """
    return (
        f"{field} looks like {label}, and VardKey never stores wallet secrets. "
        "Nothing was saved; remove it and try again."
    )


def _token_secret(token):
    """Return the label of a key-shaped token, or ``None``."""
    if not all(character in BASE58 for character in token):
        return None
    folded = token.lower()
    if (
        folded.startswith(EXTENDED_PRIVATE_KEY_PREFIXES)
        and len(token) >= EXTENDED_PRIVATE_KEY_MIN_LENGTH
    ):
        return "an extended private key"
    if token[:1] in WIF_PREFIXES and len(token) in WIF_LENGTHS:
        return "a private key"
    if folded.startswith(BIP38_PREFIX) and len(token) == BIP38_LENGTH:
        return "an encrypted private key"
    return None


def _has_mnemonic_run(text):
    """Return True when the text holds a run of BIP39 words long enough to be a phrase.

    The run is counted over the words of the text, so a phrase that is pasted in
    the middle of a sentence is still recognised. Anything that is not a letter
    breaks the run, so an ordinary sentence rarely reaches the threshold.
    """
    run = 0
    for word in WORD.findall(text):
        if word.lower() in _BIP39_LOOKUP:
            run += 1
            if run >= MNEMONIC_MIN_WORDS:
                return True
        else:
            run = 0
    return False
