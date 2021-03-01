import shutil
import threading
import time

import jsonpickle
import pandas as pd
import yaml

from app.algo import local_computation, global_aggregation


class AppLogic:

    def __init__(self):
        # === Status of this app instance ===

        # Indicates whether there is data to share, if True make sure self.data_out is available
        self.status_available = False

        # Will stop execution when True
        self.status_finished = False

        # === Data ===
        self.data_incoming = []
        self.data_outgoing = None

        # === Parameters set during setup ===
        self.id = None
        self.coordinator = None
        self.clients = None

        # === Directories, input files always in INPUT_DIR. Write your output always in OUTPUT_DIR
        self.INPUT_DIR = "/mnt/input"
        self.OUTPUT_DIR = "/mnt/output"

        # === Variables from config.yml
        self.input_filename = None
        self.sep = None
        self.output_filename = None

        # === Internals ===
        self.thread = None
        self.iteration = 0
        self.progress = "not started yet"
        self.local_result = None
        self.global_result = None

    def handle_setup(self, client_id, master, clients):
        # This method is called once upon startup and contains information about the execution context of this instance
        self.id = client_id
        self.coordinator = master
        self.clients = clients
        print(f"Received setup: {self.id} {self.coordinator} {self.clients}", flush=True)

        self.thread = threading.Thread(target=self.app_flow)
        self.thread.start()

    def handle_incoming(self, data):
        # This method is called when new data arrives
        print("Process incoming data....", flush=True)
        self.data_incoming.append(data.read())

    def handle_outgoing(self):
        print("Process outgoing data...", flush=True)
        # This method is called when data is requested
        self.status_available = False
        return self.data_outgoing

    def read_config(self):
        with open(self.INPUT_DIR + "/config.yml") as f:
            config = yaml.load(f, Loader=yaml.FullLoader)["fc_template"]
            self.input_filename = config["files"]["input_filename"]
            self.sep = config["files"]["sep"]
            self.output_filename = config["files"]["output_filename"]
        shutil.copyfile(self.INPUT_DIR + "/config.yml", self.OUTPUT_DIR + "/config.yml")
        print(f"Read config file.", flush=True)

    def app_flow(self):
        # This method contains a state machine for the participant and coordinator instance

        # === States ===
        state_initializing = 1
        state_read_input = 2
        state_local_computation = 3
        state_wait_for_aggregation = 4
        state_global_aggregation = 5
        state_finish = 6

        # Initial state
        state = state_initializing
        while True:

            if state == state_initializing:
                self.progress = "initializing..."
                print("[CLIENT] Initializing...", flush=True)
                if self.id is not None:  # Test is setup has happened already
                    if self.coordinator:
                        print("I am the coordinator.", flush=True)
                    else:
                        print("I am a participating client.", flush=True)
                    state = state_local_computation
                print("[CLIENT] Initializing finished.", flush=True)

            if state == state_read_input:
                self.progress = "read input..."
                print("[CLIENT] Read input...", flush=True)
                self.read_config()
                state = state_local_computation
                print("[CLIENT] Read input finished.", flush=True)

            if state == state_local_computation:
                self.progress = "compute local results..."
                print("[CLIENT] Compute local results...", flush=True)
                self.progress = 'computing...'
                local_results = local_computation()
                data_to_send = jsonpickle.encode(local_results)

                if self.coordinator:
                    self.data_incoming.append(data_to_send)
                    state = state_global_aggregation
                else:
                    self.data_outgoing = data_to_send
                    self.status_available = True
                    state = state_wait_for_aggregation
                    print('[CLIENT] Send data to coordinator', flush=True)
                print("[CLIENT] Compute local results finished.", flush=True)

            if state == state_wait_for_aggregation:
                self.progress = "wait for aggregated results..."
                print("[CLIENT] Wait for aggregated results from coordinator...", flush=True)
                self.progress = 'wait for aggregation'
                if len(self.data_incoming) > 0:
                    print("[CLIENT] Process aggregated result from coordinator...", flush=True)
                    self.global_result = jsonpickle.decode(self.data_incoming[0])
                    self.data_incoming = []
                    state = state_finish
                    print("[CLIENT] Processing aggregated results finished.", flush=True)

            # GLOBAL AGGREGATION
            if state == state_global_aggregation:
                self.progress = "aggregate results..."
                print("[COORDINATOR] Aggregate local results to a global result...", flush=True)
                self.progress = 'Global aggregation...'
                if len(self.data_incoming) == len(self.clients):
                    print("[COORDINATOR] Received data of all participants.", flush=True)
                    print("[COORDINATOR] Aggregate results...", flush=True)
                    data = [jsonpickle.decode(client_data) for client_data in self.data_incoming]
                    self.data_incoming = []
                    self.global_result = global_aggregation(data)
                    data_to_broadcast = jsonpickle.encode(self.global_result)
                    self.data_outgoing = data_to_broadcast
                    self.status_available = True
                    state = state_finish
                    print("COORDINATOR] Global aggregation finished.", flush=True)
                else:
                    print(
                        f"[COORDINATOR] Data of {str(len(self.clients) - len(self.data_incoming))} client(s) still "
                        f"missing...)", flush=True)

            if state == state_finish:
                self.progress = "finishing..."
                print("[CLIENT] FINISHING", flush=True)
                self.progress = 'finishing...'
                print(f"Final result: {self.global_result}")
                f = open(f"{self.OUTPUT_DIR}/result.txt", "w")
                f.write(str(self.global_result))
                f.close()
                if self.coordinator:
                    time.sleep(5)
                self.status_finished = True
                self.progress = "finished."
                break

            time.sleep(1)


logic = AppLogic()
