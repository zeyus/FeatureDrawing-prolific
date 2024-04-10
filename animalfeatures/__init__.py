from sqlalchemy.ext.declarative import DeclarativeMeta  # type: ignore
from otree.api import BaseConstants, BaseSubsession, BaseGroup, BasePlayer, models, Page, ExtraModel  # type: ignore
from otree.models import Participant  # type: ignore
from random import shuffle, choice
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
        },
        'narrative': {
            'trial_title': 'Draw the selected animal so that another participant can easily recognize its behavior',
            'stim_dir': 'img/cond_n/',
            'by_animal': True,
        },
        'aesthetic': {
            'trial_title': 'Draw the selected animal so that another participant will find your drawing pleasing to the eye',
            'stim_dir': 'img/cond_r_a/',
            'by_animal': False,
        },
    }


def get_condition_config(condition: str):
    return C.CONDITION_CONFIG[condition]


class Subsession(BaseSubsession, metaclass=AnnotationFreeMeta):
    pass


class Group(BaseGroup, metaclass=AnnotationFreeMeta):
    pass


class Player(BasePlayer, metaclass=AnnotationFreeMeta):
    uas: str = models.StringField()
    wx: float = models.FloatField()
    wy: float = models.FloatField()
    orientation: str = models.StringField()
    browser: str = models.StringField()
    browser_version: str = models.StringField()
    os: str = models.StringField()
    os_version: str = models.StringField()
    device: str = models.StringField()
    device_brand: str = models.StringField()
    device_model: str = models.StringField()



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
    animal: int = models.StringField(initial="")  # type: ignore
    action: int = models.StringField(initial="")  # type: ignore
    completed: bool = models.BooleanField(initial=False)  # type: ignore


def creating_session(subsession):
    if subsession.round_number == 1:
        condition = None
        # if the condition is specified by the demo session (for testing) we will use that
        if 'condition' in subsession.session.config and subsession.session.config['condition'] is not None:
            condition = subsession.session.config['condition']
        # set up the condition for each participant
        for player in subsession.get_players():
            participant = player.participant
            # randomly select a condition if not specified
            participant.condition = choice(C.CONDITIONS) if condition is None else condition
            # set up the order of the stimuli
            stim_order = ['_'.join([animal, action]) for animal in C.ANIMALS for action in C.ANIMAL_ACTIONS]
            # randomize the order of the stimuli
            shuffle(stim_order)
            # save the order of the stimuli
            participant.stim_order = base64.b64encode(''.join(stim_order).encode()).decode()
            # set up the stimuli for this round
            for i in range(1, C.NUM_ROUNDS + 1):
                print("creating drawing object for ", player.id_in_group, " round ", i)
                animal, action = stim_order.pop().split('_')
                Drawing.create(
                    participant=participant,
                    trial=i,
                    condition=participant.condition,
                    animal=animal,
                    action=action,
                )

def get_current_trial(player: Player) -> Drawing:
    print("getting current trial for participant_id: ", player.participant.id, " round: ", player.round_number)
    print("subsession round number: ", player.subsession.round_number)
    drawing = Drawing.filter(participant=player.participant, trial=player.subsession.round_number)[0]
    print("got drawing: ", drawing.id)
    return drawing


def get_stimuli_for_round(drawing: Drawing) -> list[dict]:
    selected_animal = drawing.animal
    selected_action = drawing.action
    condition = drawing.condition
    condition_config = get_condition_config(condition)
    stimuli = []
    file_ext = 'gif' if condition == 'narrative' else 'png'
    # if we display stimuli by animal, we will show all actions for that animal
    if condition_config['by_animal']:
        for action in C.ANIMAL_ACTIONS:
            selected = action == selected_action
            stimuli.append({
                'animal': selected_animal,
                'action': action,
                'selected': selected,
                'class': 'selected' if selected else '',
                'stim': f"{condition_config['stim_dir']}{selected_animal}_{action}.{file_ext}",
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
                'stim': f"{condition_config['stim_dir']}{animal}_{selected_action}.{file_ext}",
            })
    # shuffle the stimuli
    shuffle(stimuli)
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
            user_agent: UserAgent = parse(player.participant.user_agent)
        except Exception:
            # catch any error because we can just return unknown
            return

        player.browser = user_agent.browser.family
        player.browser_version = user_agent.browser.version_string
        player.os = user_agent.os.family
        player.os_version = user_agent.os.version_string
        player.device = user_agent.device.family
        player.device_brand = user_agent.device.brand
        player.device_model = user_agent.device.model


    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        ScreenInfoMixin.update_browser_info(player)


# PAGES
class Welcome(Page, ScreenInfoMixin):


    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


class Consent(Page, ScreenInfoMixin):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


class Instructions(Page, ScreenInfoMixin):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


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


class Stimulus(Page, ScreenInfoMixin):
    @staticmethod
    def vars_for_template(player: Player):
        return StimPage.vars_for_template(player)


class Draw(Page, ScreenInfoMixin):
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

class ThankYou(Page, ScreenInfoMixin):
    @staticmethod
    # only display this page on the last round
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

page_sequence = [Welcome, Consent, Instructions, Stimulus, Draw, ThankYou]

# data out
# animal, action, condition, stim_img (animal_action{.gif if narrative else .png}), drawing_time, start_timestamp, end_timestamp, completed

def custom_export(players):
    yield [
        'participant_code',
        'condition',
        'trial',
        'animal',
        'action',
        'img'
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
        'svg',
    ]
