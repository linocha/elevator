import math
import random
import numpy as np

INQUEUE = 0         # человек ожидает лифт
INELEVATOR = 1      # человек находится в лифте
INPROCESS = 2       # человек в процессе генерации
UP = 1              # лифт поднимается
DOWN = 0            # лифт опускается
WAIT = 2            # лифт ждет

modelTime = 3600
peopePer1Floor = 60 / 20
peopePerNFloor = 60 / 1
timePerFloor = 5
timeMinToDrop = 7
timeToDrop = 10

floorCount = 21
elevatorCount = 4

waittime = [[] for _ in range(floorCount)]


class Human(object):
    def __init__(self, curfloor, destfloor, curtime):
        self.state = INPROCESS                              # состояние человека (INQUEUE, INELEVATOR, INPROCESS)
        self.curFloor = curfloor                            # этаж, на котором он находится
        self.destFloor = destfloor                          # этаж, куда ему нужно
        self.nextEvent = self.get_rand_time() + curtime     # выставляем время "прибытия" в холл

    def get_rand_time(self):
        if self.curFloor == 0:
            return random.expovariate(1 / peopePer1Floor)
        else:
            return random.expovariate(1 / peopePerNFloor)

    def set_state(self, state, ct):
        self.state = state
        if state == INELEVATOR:
            waittime[self.curFloor].append(ct - self.nextEvent)

    def get_next_event(self):
        return self.nextEvent

    def get_dest_floor(self):
        return self.destFloor

    def get_cur_floor(self):
        return self.curFloor


# класс лифта
class Elevator(object):
    def __init__(self, allocation):
        self.bottomFloor = allocation[0]                    # нижняя граница
        self.topFloor = allocation[1]                       # верхняя граница
        self.currentFloor = 0                               # текущий этаж
        self.state = UP                                     # состояние (UP - движение наверх; DOWN - движение вниз)
        self.queueUP = []                                   # очередь в лифт
        self.queueDOWN = []
        self.inside = []
        self.peopleCount = 0
        self.nextEvent = 0                                  # следующее событие
        self.up = 0

    def set_state(self, state):
        self.state = state

    def get_next_event(self):
        return self.nextEvent


# экспоненциальное распределение
def exponential_distribution(min, middle):
    while True:
        r = random.expovariate(1 / middle)
        if r > min:
            return math.floor(r)


# загрузка людей на 1 этаже
def loading_1_floor(e, ct):
    delay = exponential_distribution(timeMinToDrop, timeToDrop)     # задержка на загрузку/выгрузку пассажирв
    for human in e.queueUP:
        if human.state == INQUEUE:                          # если человек не уехал
            e.inside.append(human)                          # добавляем человека в лифт
            human.set_state(INELEVATOR, ct)
            e.peopleCount += 1                              # увеличиваем счетчик людей в лифте
        e.queueUP.pop(e.queueUP.index(human))               # убираем человека из очереди в любом случае
        if len(e.inside) == 20:                             # если количество людей в лифте = 20
            break
    if len(e.inside) > 0:                                   # если он кого то забрал
        e.set_state(UP)  # состояние "движение наверх"
        e.up += 1
        # e.inside = sorted(e.inside, key=lambda h: h.get_dest_floor)     # сортируем людей по конечному этажу
        e.nextEvent = ct + delay + timePerFloor * e.inside[0].get_dest_floor()  # ставим метку на следующее событие
        e.currentFloor = e.inside[0].get_dest_floor()                   # устанавливаем этаж лифта на первого чел-ка
    else:
        e.nextEvent = ct + 1
        e.set_state(WAIT)


# выгрузка людей на этажах
def drop_up(e, ct):
    while True:                                                         # пока есть люди, которым нужно выходить
        e.inside.pop(0)                                                 # выгрузка пассажира
        if len(e.inside) == 0:                                          # если людей не осталось
            break
        else:
            if e.inside[0].get_dest_floor() == e.currentFloor:          # если есть люди, которым нужно выходить
                continue                                                # выходит следующий человек
            else:                                                       # иначе конец цикла
                break
    # если в лифте остались люди, то ставится метка на следующее событие
    # и увеличивается этаж лифта
    if len(e.inside) > 0:
        e.nextEvent = ct + timePerFloor * (e.inside[0].get_dest_floor() - e.currentFloor)
        e.currentFloor = e.inside[0].get_dest_floor()
    # если лифт пустой и есть очередь вниз, то состояние лифта меняется на "движение вниз"
    # устанавливается метка на следующее событие и увеличивается этаж
    elif len(e.queueDOWN) > 0:
        e.set_state(DOWN)
        e.nextEvent = ct + timePerFloor * (e.queueDOWN[0].get_cur_floor() - e.currentFloor)
        e.currentFloor = e.queueDOWN[0].get_cur_floor()
    else:
        e.nextEvent = ct + 1
        e.set_state(WAIT)


# загрузка на остальных этажах при движении вниз
def loading_down(e, ct):
    for h in e.queueDOWN:
        # загрузка в лифт всех людей, которые находятся на том же этаже, что и лифт
        if h.get_cur_floor() == e.currentFloor and h.state == INQUEUE and len(e.inside) < 20:
            h.set_state(INELEVATOR, ct)
            e.queueDOWN.pop(e.queueDOWN.index(h))
            e.peopleCount += 1
            e.inside.append(h)

    # ищем этаж, на который следующим спустится лифт
    # максимальный этаж, который ниже текущего
    max = 0
    for h in e.queueDOWN:
        if e.currentFloor > h.get_cur_floor() > max:
            max = h.get_cur_floor()
    # если таких этажей нет, то лифт спускается на первый
    if max == 0:
        e.nextEvent = ct + timePerFloor * e.currentFloor
        e.currentFloor = 0
        e.inside = []
        e.set_state(WAIT)
    # если такой этаж есть, тогда лифт спускается вниз
    else:
        e.nextEvent = ct + timePerFloor * (e.currentFloor - max)
        e.currentFloor = max


# проверка очереди (в какую сторону поедет лифт)
def check_queue(e, ct):
    if len(e.queueUP) > 0:
        e.set_state(UP)
    elif len(e.queueDOWN) > 0:
        e.set_state(DOWN)
    else:
        e.nextEvent = ct + 1


# возвоащает случайный этаж в распределении от 1 до верхнего этажа
def get_floor():
    random.seed()
    return random.randint(1, floorCount - 1)


# создание будущего появления человека в лифтовом холле
# в зависимости от направления движения
def make_human(state, curtime, curfloor):
    return Human(0, get_floor(), curtime) if state == UP else Human(curfloor, 0, curtime)


def generate_human_in_process(nexteventlist, ct, curfloor):
    if curfloor == 0:
        nexteventlist.append(make_human(UP, ct, curfloor))
    else:
        nexteventlist.append(make_human(DOWN, ct, curfloor))
    return nexteventlist


def generate_human_in_queue(nexteventlist, elv):
    human = nexteventlist.pop(0)
    ct = human.get_next_event()
    human.set_state(INQUEUE, ct)  # состояние - в очереди
    # human.nextEvent = 0                                     # следующее событие не известно
    if human.destFloor != 0:  # если человек едет наверх
        for e in elv:  # ставим человека в очередь к нужным лифтам
            if e.bottomFloor <= human.destFloor <= e.topFloor:
                e.queueUP.append(human)
                e.queueUP = sorted(e.queueUP, key=lambda h: h.get_dest_floor())

    else:
        # если человек едет вниз, то проверяем возможность
        # вставания в очередь в каждый из доступных лифтов
        for e in elv:
            if e.bottomFloor <= human.curFloor <= e.topFloor:
                e.queueDOWN.append(human)
                e.queueDOWN = sorted(e.queueDOWN, key=lambda h: h.get_cur_floor(), reverse=True)
    nexteventlist = generate_human_in_process(nexteventlist, ct, human.curFloor)    # генерируем следующего человека на этаже
    return nexteventlist


def simulate(elevators):
    nextEventList = []
    for i in range(floorCount):
        nextEventList = generate_human_in_process(nextEventList, 0, i)
    for elevator in elevators:
        nextEventList.append(elevator)
    nextEventList = sorted(nextEventList, key=lambda obj: obj.get_next_event())
    while True:
        obj = nextEventList[0]
        if obj.__class__.__name__ == 'Human':
            nextEventList = generate_human_in_queue(nextEventList, elevators)
        else:
            curtime = obj.get_next_event()
            # если лифт на первом этаже
            if obj.state == WAIT:
                check_queue(obj, curtime)
            if obj.currentFloor == 0:
                loading_1_floor(obj, curtime)
            elif obj.state == UP:
                drop_up(obj, curtime)
            # иначе загрузить пассажиров в лифт
            if obj.state == DOWN:
                loading_down(obj, curtime)
        nextEventList = sorted(nextEventList, key=lambda obj: obj.get_next_event())
        if nextEventList[0].get_next_event() > modelTime:
            break


if __name__ == '__main__':
    ElevatorAllocation = [[1, 20], [1, 20], [1, 20], [1, 20]]
    print('elevator allocation', ElevatorAllocation)
    Elevators = []
    for i in range(elevatorCount):
        Elevators.append(Elevator(ElevatorAllocation[i]))
    simulate(Elevators)
    # print(waittime)
    for i in waittime:
        print(np.mean(i))
