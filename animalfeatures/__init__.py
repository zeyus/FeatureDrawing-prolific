from sqlalchemy.ext.declarative import DeclarativeMeta  # type: ignore
from otree.api import BaseConstants, BaseSubsession, BaseGroup, BasePlayer, models, Page, ExtraModel  # type: ignore
from otree.models import Participant  # type: ignore
from random import shuffle, randint
import base64
import datetime
from user_agents import parse  # type: ignore
from user_agents.parsers import UserAgent  # type: ignore


doc = """
A drawing experiment to help understand the motivation and purpose of the El Castillo animal depictions from the perspective of the producer.
"""

class AnnotationFreeMeta(DeclarativeMeta):
    """Metaclass to remove the __annotations__ attribute from the class
    this fixes an error where oTree tries to use __annotations__ and thinks it's a dict
    that needs saving.
    """

    def __new__(cls, name, bases, dct):
        dct.pop("__annotations__", None)
        return super().__new__(cls, name, bases, dct)

class C(BaseConstants):
    NAME_IN_URL = 'animalfeatures'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 16
    DRAWING_TIME = 120.0
    CONDITIONS = ['species_recognition', 'narrative', 'aesthetic']
    ANIMALS = ['horse', 'bison', 'ibex', 'deer']
    ANIMAL_ACTIONS = ['lie', 'run', 'stretch', 'walk']
    CONDITION_CONFIG = {
        'species_recognition': {
            'trial_title': 'Draw the selected animal so that another participant can easily recognize that it is this particular animal that you are communicating',
            'stim_dir': 'img/cond_r_a/',
            'by_animal': False,
            'file_ext': 'png',
        },
        'narrative': {
            'trial_title': 'Draw the selected animal so that another participant can easily recognize its behavior',
            'stim_dir': 'img/cond_n/',
            'by_animal': True,
            'file_ext': 'gif',
        },
        'aesthetic': {
            'trial_title': 'Draw the selected animal so that another participant will find your drawing pleasing to the eye',
            'stim_dir': 'img/cond_r_a/',
            'by_animal': False,
            'file_ext': 'png',
        },
    }
    # will use the session config but will fall back to the following
    PROLIFIC_FALLBACK_URL = 'https://app.prolific.com/submissions/complete?cc=CW8BWO89'


def get_condition_config(condition: str):
    return C.CONDITION_CONFIG[condition]


class Subsession(BaseSubsession, metaclass=AnnotationFreeMeta):
    pass


class Group(BaseGroup, metaclass=AnnotationFreeMeta):
    pass


class Player(BasePlayer, metaclass=AnnotationFreeMeta):
    uas: str = models.StringField(initial="N/A")  # type: ignore
    wx: str = models.StringField(initial="N/A")  # type: ignore
    wy: str = models.StringField(initial="N/A")  # type: ignore
    orientation: str = models.StringField(initial="N/A")  # type: ignore
    prolific_id: str = models.StringField(initial="N/A")  # type: ignore
    input_device: int = models.IntegerField(
        label='What are you using to draw?',
        choices=[
            [0, 'Mouse'],
            [1, 'Touchpad'],
            [2, 'Touchscreen (finger)'],
            [3, 'Touchscreen (stylus)'],
            [4, 'Graphics Tablet'],
            [5, 'Trackball'],
            [6, 'Joystick or Gamepad'],
            [7, 'Other'],
        ]
    )  # type: ignore

    def field_display(self, name):
        if name == 'input_device':
            val = self.input_device
            if val is None:
                return "N/A"
        return super().field_display(name)


class Drawing(ExtraModel, metaclass=AnnotationFreeMeta):
    # subsess: Subsession = models.Link(Subsession)
    participant: Participant = models.Link(Participant)
    trial: int = models.IntegerField()
    svg: str = models.LongStringField(initial="")  # type: ignore
    drawing_time: float = models.FloatField(initial=0.0)  # type: ignore
    start_timestamp: float = models.FloatField(initial=0.0)  # type: ignore
    end_timestamp: float = models.FloatField(initial=0.0)  # type: ignore
    trial: int = models.IntegerField(initial=0)  # type: ignore
    condition: str = models.StringField(initial="")  # type: ignore
    animal: str = models.StringField(initial="")  # type: ignore
    action: str = models.StringField(initial="")  # type: ignore
    completed: bool = models.BooleanField(initial=False)  # type: ignore
    wx: str = models.StringField(initial="N/A")  # type: ignore
    wy: str = models.StringField(initial="N/A")  # type: ignore
    orientation: str = models.StringField(initial="N/A")  # type: ignore
    browser: str = models.StringField(initial="N/A")  # type: ignore
    browser_version: str = models.StringField(initial="N/A")  # type: ignore
    os: str = models.StringField(initial="N/A")  # type: ignore
    os_version: str = models.StringField(initial="N/A")  # type: ignore
    device: str = models.StringField(initial="N/A")  # type: ignore
    device_brand: str = models.StringField(initial="N/A")  # type: ignore
    device_model: str = models.StringField(initial="N/A")  # type: ignore


def creating_session(subsession):
    if subsession.round_number == 1:
        condition = None
        n_conds = len(C.CONDITIONS)
        rand_start = randint(0, n_conds - 1)
        # if the condition is specified by the demo session (for testing) we will use that
        if 'condition' in subsession.session.config and subsession.session.config['condition'] is not None:
            condition = subsession.session.config['condition']
        # set up the condition for each participant
        for n, player in enumerate(subsession.get_players()):
            participant = player.participant
            # # randomly select a condition if not specified
            # participant.condition = choice(C.CONDITIONS) if condition is None else condition
            # cycle through the conditions
            if condition is None:
                participant.condition = C.CONDITIONS[(n + rand_start) % n_conds]
            else:
                participant.condition = condition
            print("setting condition for ", player.participant.id, " to ", participant.condition)
            # set up the order of the stimuli
            stim_order = ['_'.join([animal, action]) for animal in C.ANIMALS for action in C.ANIMAL_ACTIONS]
            # randomize the order of the stimuli
            shuffle(stim_order)
            # save the order of the stimuli
            # participant.stim_order = base64.b64encode(''.join(stim_order).encode()).decode()
            # set up the stimuli for this round
            for i in range(1, C.NUM_ROUNDS + 1):
                print("creating drawing object for ", player.participant.id, " round ", i)
                animal, action = stim_order.pop().split('_')
                Drawing.create(
                    participant=participant,
                    trial=i,
                    condition=condition,
                    animal=animal,
                    action=action,
                )

def get_current_trial(player: Player, round_number: int|None = None) -> Drawing:
    round_number = player.subsession.round_number if round_number is None else round_number
    print("getting current trial for participant_id: ", player.participant.id, " round: ", round_number)
    print("subsession round number: ", player.subsession.round_number)
    drawing = Drawing.filter(participant=player.participant, trial=round_number)[0]
    print("got drawing: ", drawing.id)
    return drawing


def get_stimuli_for_round(drawing: Drawing) -> list[dict[str, object]]:
    selected_animal = drawing.animal
    selected_action = drawing.action
    condition = drawing.condition
    condition_config = get_condition_config(condition)
    stimuli = get_stimuli_set(selected_animal, selected_action, condition_config)
    shuffle(stimuli)
    return stimuli

def get_stimuli_set(selected_animal: str, selected_action: str, condition_config: dict[str, str]) -> list[dict[str, object]]:
    stimuli = []
    # if we display stimuli by animal, we will show all actions for that animal
    if condition_config['by_animal']:
        for action in C.ANIMAL_ACTIONS:
            selected = action == selected_action
            stimuli.append({
                'animal': selected_animal,
                'action': action,
                'selected': selected,
                'class': 'selected' if selected else '',
                'stim': f"{condition_config['stim_dir']}{selected_animal}_{action}.{condition_config['file_ext']}",
            })
    # otherwise we will show all animals for the selected action
    else:
        for animal in C.ANIMALS:
            selected = animal == selected_animal
            stimuli.append({
                'animal': animal,
                'action': selected_action,
                'selected': selected,
                'class': 'selected' if selected else '',
                'stim': f"{condition_config['stim_dir']}{animal}_{selected_action}.{condition_config['file_ext']}",
            })
    # shuffle the stimuli
    
    return stimuli


class ScreenInfoMixin:
    form_model = 'player'
    form_fields = ['uas', 'wx', 'wy', 'orientation']


    @staticmethod
    def update_browser_info(player: Player) -> None:
        try:
            if player.uas is None or player.uas == '':
                return
        except KeyError:
            return

        try:
            user_agent: UserAgent = parse(player.uas)
        except Exception:
            # catch any error because we can just return unknown
            return

        drawing = get_current_trial(player)
        drawing.browser = user_agent.browser.family if user_agent.browser.family is not None else "N/A"
        drawing.browser_version = user_agent.browser.version_string if user_agent.browser.version_string is not None else "N/A"
        drawing.os = user_agent.os.family if user_agent.os.family is not None else "N/A"
        drawing.os_version = user_agent.os.version_string if user_agent.os.version_string is not None else "N/A"
        drawing.device = user_agent.device.family if user_agent.device.family is not None else "N/A"
        drawing.device_brand = user_agent.device.brand if user_agent.device.brand is not None else "N/A"
        drawing.device_model = user_agent.device.model if user_agent.device.model is not None else "N/A"
        drawing.wx = player.wx
        drawing.wy = player.wy
        drawing.orientation = player.orientation


    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        ScreenInfoMixin.update_browser_info(player)


# PAGES
class InputDevice(Page):
    form_model = 'player'
    form_fields = ['input_device']

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1


class Welcome(Page):

    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1
    
    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        player.prolific_id = player.participant.label


class Consent(Page):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


class InstructionsCond(Page):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        condition_config = get_condition_config(player.participant.condition)
        stimuli = get_stimuli_set('deer', 'lie', condition_config)
        # order stimuli so that the selected animal is first
        stimuli = sorted(stimuli, key=lambda x: (x['selected'], x['animal'], x['action']), reverse=True)
        return dict(
            page_title = condition_config['trial_title'],
            stimuli = stimuli,
            condition = player.participant.condition,
        )
    
class InstructionsDraw(Page):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        condition_config = get_condition_config(player.participant.condition)
        return dict(
            condition = player.participant.condition,
            page_title = condition_config['trial_title'],
        )


class StimPage:
    @staticmethod
    def vars_for_template(player: Player):
        # get the current trial
        drawing = get_current_trial(player)
        # get the stimuli for this round
        stimuli = get_stimuli_for_round(drawing)
        # get the condition config
        condition_config = get_condition_config(player.participant.condition)
        return dict(
            page_title = condition_config['trial_title'],
            stimuli = stimuli,
        )


class Stimulus(Page):
    @staticmethod
    def vars_for_template(player: Player):
        return StimPage.vars_for_template(player)


class Draw(ScreenInfoMixin, Page):
    # only display this page if the trial is not completed
    @staticmethod
    def is_displayed(player: Player):
        drawing = get_current_trial(player)
        # sneakily update the drawing time if the drawing is not completed
        if not drawing.completed and drawing.start_timestamp > 0.0:
            drawing.drawing_time = datetime.datetime.now().timestamp() - drawing.start_timestamp
        if drawing.drawing_time > C.DRAWING_TIME:
            drawing.completed = True
            drawing.end_timestamp = datetime.datetime.now().timestamp()

        return not drawing.completed

    @staticmethod
    def vars_for_template(player: Player):
        # get the condition config
        condition_config = get_condition_config(player.participant.condition)
        # get the current trial
        return dict(
            page_title = condition_config['trial_title'],
        )
    
    @staticmethod
    def live_method(player, data):
        # get the current trial
        drawing = get_current_trial(player)
        if "event" in data:
            print("received event: ", data["event"])
            if data['event'] == 'init':
                # start the drawing timer
                if drawing.start_timestamp == 0.0:
                    drawing.start_timestamp = datetime.datetime.now().timestamp()
                drawing.drawing_time = datetime.datetime.now().timestamp() - drawing.start_timestamp
                return {
                        player.id_in_group: dict(
                            event='init',
                            time_left=C.DRAWING_TIME - drawing.drawing_time,
                            drawing=base64.b64encode(drawing.svg.encode('utf-8')).decode('utf-8'),
                            completed=drawing.completed,
                        )
                    }
            elif data["event"] == "update":
                print("updating drawing for ", player.id_in_group)
                drawing.svg = base64.b64decode(data["drawing"]).decode('utf-8')
                # no return
            elif data["event"] == "drawing_complete":
                drawing.end_timestamp = datetime.datetime.now().timestamp()
                drawing.svg = base64.b64decode(data["drawing"]).decode('utf-8')
                drawing.drawing_time = drawing.end_timestamp - drawing.start_timestamp
                drawing.completed = True
                # send confirmation to the client
                print("drawing complete for ", player.id_in_group)
                return {
                    player.id_in_group: dict(
                        event='drawing_complete',
                        time_left=0,
                        drawing=drawing.svg,
                        completed=True,
                    )
                }

class ThankYou(Page):
    @staticmethod
    # only display this page on the last round
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            prolific_url = C.PROLIFIC_FALLBACK_URL if 'prolific_url' not in player.session.config else player.session.config['prolific_url'],
        )

page_sequence = [Welcome, Consent, InputDevice, InstructionsCond, InstructionsDraw, Stimulus, Draw, ThankYou]

# data out
# animal, action, condition, stim_img (animal_action{.gif if narrative else .png}), drawing_time, start_timestamp, end_timestamp, completed

def custom_export(players):
    for player in players:
        # assign condition to player
        drawing = get_current_trial(player, 1)
        if not hasattr(player, 'condition') or player.condition is None:
            player.condition = drawing.condition
        if 'condition' not in player.participant.vars or player.participant.vars['condition'] is None:
            player.participant.vars['condition'] = drawing.condition

    yield [
        'participant_code',
        'prolific_id',
        'condition',
        'trial',
        'animal',
        'action',
        'stim_img',
        'drawing_time',
        'start_timestamp',
        'end_timestamp',
        'completed',
        'browser',
        'browser_version',
        'os',
        'os_version',
        'device',
        'device_brand',
        'device_model',
        'window_width',
        'window_height',
        'orientation',
        'input_device',
        'svg',
    ]

    for drawing in Drawing.filter():
        player = drawing.participant.get_players()[0]
        # failsafe for older models that didn't have condition on drawing, or participant, fall back to N/A
        condition = "N/A"
        # check if drawing has a condition prop
        if hasattr(drawing, 'condition'):
            condition = drawing.condition
            condition_conf = get_condition_config(condition)
        elif hasattr(player.participant, 'condition'):
            condition = player.condition
            condition_conf = get_condition_config(condition)
        else:
            condition = "N/A"
            condition_conf = dict(
                file_ext='png'
            )
        # condition_conf = get_condition_config(drawing.condition)
        yield [
            player.participant.code,
            player.prolific_id,
            drawing.condition,
            drawing.trial,
            drawing.animal,
            drawing.action,
            f"{drawing.animal}_{drawing.action}.{condition_conf['file_ext']}",
            drawing.drawing_time,
            drawing.start_timestamp,
            drawing.end_timestamp,
            drawing.completed,
            drawing.browser,
            drawing.browser_version,
            drawing.os,
            drawing.os_version,
            drawing.device,
            drawing.device_brand,
            drawing.device_model,
            drawing.wx,
            drawing.wy,
            drawing.orientation,
            player.field_display('input_device'),
            drawing.svg,
        ]
