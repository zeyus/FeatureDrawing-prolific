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
    browser: str = models.StringField(initial="N/A")  # type: ignore
    browser_version: str = models.StringField(initial="N/A")  # type: ignore
    os: str = models.StringField(initial="N/A")  # type: ignore
    os_version: str = models.StringField(initial="N/A")  # type: ignore
    device: str = models.StringField(initial="N/A")  # type: ignore
    device_brand: str = models.StringField(initial="N/A")  # type: ignore
    device_model: str = models.StringField(initial="N/A")  # type: ignore



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
class Welcome(ScreenInfoMixin, Page):


    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


class Consent(ScreenInfoMixin, Page):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1


class InstructionsCond(ScreenInfoMixin, Page):
    @staticmethod
    # only display this page on the first round
    def is_displayed(player: Player):
        return player.round_number == 1
    
    @staticmethod
    def vars_for_template(player: Player):
        condition_config = get_condition_config(player.participant.condition)
        stimuli = get_stimuli_set('deer', 'lie', condition_config)
        return dict(
            page_title = condition_config['trial_title'],
            stimuli = stimuli,
            condition = player.participant.condition,
        )
    
class InstructionsDraw(ScreenInfoMixin, Page):
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


class Stimulus(ScreenInfoMixin, Page):
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

class ThankYou(Page, ScreenInfoMixin):
    @staticmethod
    # only display this page on the last round
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

page_sequence = [Welcome, Consent, InstructionsCond, InstructionsDraw, Stimulus, Draw, ThankYou]

# data out
# animal, action, condition, stim_img (animal_action{.gif if narrative else .png}), drawing_time, start_timestamp, end_timestamp, completed

def custom_export(players):
    yield [
        'participant_code',
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
        'svg',
    ]

    for player in players:
        for drawing in Drawing.filter(participant=player.participant):
            yield [
                player.participant.code,
                player.participant.condition,
                drawing.trial,
                drawing.animal,
                drawing.action,
                f"{drawing.animal}_{drawing.action}.gif" if player.participant.condition == 'narrative' else f"{drawing.animal}_{drawing.action}.png",
                drawing.drawing_time,
                drawing.start_timestamp,
                drawing.end_timestamp,
                drawing.completed,
                player.browser,
                player.browser_version,
                player.os,
                player.os_version,
                player.device,
                player.device_brand,
                player.device_model,
                player.wx,
                player.wy,
                player.orientation,
                drawing.svg,
            ]
