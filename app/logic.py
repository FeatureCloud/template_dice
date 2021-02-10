import json
import random
import threading
import time

STATE_INITIALIZING = 1

STATE_LOCAL_GATHER = 2
STATE_LOCAL_COMPUTATION = 3

STATE_GLOBAL_GATHER = 4
STATE_GLOBAL_COMPUTATION = 5

STATE_FINISHING = 6


class AppLogic:

    def __init__(self):
        # === Status of this app instance ===

        # Indicates whether there is data to share, if True make sure self.data_out is available
        self.status_available = False

        # Only relevant for master, will stop execution when True
        self.status_finished = False

        # === Parameters set during setup ===
        self.id = None
        self.master = None
        self.clients = None

        # === Data ===
        self.data_incoming = []
        self.data_outgoing = None

        # === Internals ===
        self.thread = None
        self.iteration = 0
        self.state = STATE_INITIALIZING

    def handle_setup(self, client_id, master, clients):
        self.id = client_id
        self.master = master
        self.clients = clients
        print(f'Received setup: {self.id} {self.master} {self.clients}', flush=True)

        self.thread = threading.Thread(target=self.app_flow)
        self.thread.start()

    def handle_incoming(self, data):
        self.data_incoming.append(json.load(data))

    def handle_outgoing(self):
        self.status_available = False
        return self.data_outgoing

    def app_flow(self):
        while True:

            if self.state == STATE_INITIALIZING:
                if self.id is not None:
                    if self.master:
                        self.state = STATE_GLOBAL_GATHER
                    else:
                        self.state = STATE_LOCAL_GATHER

            # LOCAL PART

            if self.state == STATE_LOCAL_GATHER:
                self.iteration += 1

                if self.iteration == 1:
                    self.state = STATE_LOCAL_COMPUTATION
                else:
                    if len(self.data_incoming) > 0:
                        print(f'[SLAVE] Got result from master: {self.data_incoming[0]}')
                        break

            if self.state == STATE_LOCAL_COMPUTATION:
                data = random.randint(1, 6)
                self.data_outgoing = json.dumps(data)
                self.status_available = True
                self.state = STATE_LOCAL_GATHER

            # GLOBAL PART

            if self.state == STATE_GLOBAL_GATHER:
                if len(self.data_incoming) == len(self.clients) - 1:
                    self.state = STATE_GLOBAL_COMPUTATION

            if self.state == STATE_GLOBAL_COMPUTATION:
                data = sum(self.data_incoming)
                print(f'[MASTER] Global sum is {data}')
                self.data_outgoing = json.dumps(data)
                self.status_available = True
                self.state = STATE_FINISHING

            if self.state == STATE_FINISHING:
                time.sleep(10)
                self.status_finished = True
                break


logic = AppLogic()
