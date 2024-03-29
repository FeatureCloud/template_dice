import shutil
import threading
import time

import jsonpickle
import yaml

from app.algo import local_computation, global_aggregation


class AppLogic:

    def __init__(self):
        # === Status of this app instance ===

        # Indicates whether there is data to share, if True make sure self.data_out is available
        self.status_available = False

        # Will stop execution when True
        self.status_finished = False

        # === Parameters set during setup ===
        self.id = None
        self.coordinator = None
        self.clients = None

        # === Data ===
        self.data_incoming = []
        self.data_outgoing = None

        # === Internals ===
        self.thread = None
        self.iteration = 0
        self.progress = "not started yet"

        # === Directories, input files always in INPUT_DIR. Write your output always in OUTPUT_DIR
        self.INPUT_DIR = "/mnt/input"
        self.OUTPUT_DIR = "/mnt/output"

        # === Variables from config.yml
        self.output_name = None

        self.local_result = None
        self.global_result = None

    def handle_setup(self, client_id, coordinator, clients):
        # This method is called once upon startup and contains information about the execution context of this instance
        self.id = client_id
        self.coordinator = coordinator
        self.clients = clients
        print(f'Received setup: {self.id} {self.coordinator} {self.clients}', flush=True)

        self.thread = threading.Thread(target=self.app_flow)
        self.thread.start()

    def handle_incoming(self, data):
        # This method is called when new data arrives
        print('Process incoming data....', flush=True)
        self.data_incoming.append(data.read())

    def handle_outgoing(self):
        print('Process outgoing data...', flush=True)
        # This method is called when data is requested
        self.status_available = False
        return self.data_outgoing

    def read_config(self):
        try:
            with open(self.INPUT_DIR + "/config.yml") as f:
                config = yaml.load(f, Loader=yaml.FullLoader)["fc_dice"]
                self.output_name = config["output_name"]
            shutil.copyfile(self.INPUT_DIR + "/config.yml", self.OUTPUT_DIR + "/config.yml")
        except:
            self.output_name = 'output.csv'

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
                    state = state_read_input
                print("[CLIENT] Initializing finished.", flush=True)

            if state == state_read_input:
                self.progress = "read input..."
                print("[CLIENT] Read input...", flush=True)
                # Read the config file
                self.read_config()
                # Here you could read in your input files
                state = state_local_computation
                print("[CLIENT] Read input finished.", flush=True)

            if state == state_local_computation:
                self.progress = "compute local results..."
                print("[CLIENT] Compute local results...", flush=True)
                self.progress = 'computing...'

                # Compute local results
                local_results = local_computation()
                # Encode local results to send it to coordinator
                data_to_send = jsonpickle.encode(local_results)

                if self.coordinator:
                    # if the client is the coordinator: add the local results directly to the data_incoming array
                    self.data_incoming.append(data_to_send)
                    # go to state where the coordinator is waiting for the local results and aggregates them
                    state = state_global_aggregation
                else:
                    # if the client is not the cooridnator: set data_outgoing and set status_available to true
                    self.data_outgoing = data_to_send
                    self.status_available = True
                    # go to state where the client is waiting for the aggregated results
                    state = state_wait_for_aggregation
                    print('[CLIENT] Send data to coordinator', flush=True)
                print("[CLIENT] Compute local results finished.", flush=True)

            if state == state_wait_for_aggregation:
                self.progress = "wait for aggregated results..."
                print("[CLIENT] Wait for aggregated results from coordinator...", flush=True)
                # Wait until received broadcast data from coordinator
                if len(self.data_incoming) > 0:
                    print("[CLIENT] Process aggregated result from coordinator...", flush=True)
                    # Decode broadcasted data
                    self.global_result = jsonpickle.decode(self.data_incoming[0])
                    # Empty incoming data
                    self.data_incoming = []
                    # Go to nex state (finish)
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
                    # Decode received data of each client
                    data = [jsonpickle.decode(client_data) for client_data in self.data_incoming]
                    # Empty the incoming data (important for multiple iterations)
                    self.data_incoming = []
                    # Perform global aggregation
                    self.global_result = global_aggregation(data)
                    # Encode aggregated results for broadcasting
                    data_to_broadcast = jsonpickle.encode(self.global_result)
                    # Fill data_outgoing
                    self.data_outgoing = data_to_broadcast
                    # Set available to True such that the data will be broadcasted
                    self.status_available = True
                    state = state_finish
                    print("[COORDINATOR] Global aggregation finished.", flush=True)
                else:
                    print(
                        f"[COORDINATOR] Data of {str(len(self.clients) - len(self.data_incoming))} client(s) still "
                        f"missing...)", flush=True)

            if state == state_finish:
                self.progress = "finishing..."
                print("[CLIENT] FINISHING", flush=True)

                # Write results
                print(f"Final result: {self.global_result}")
                f = open(f'{self.OUTPUT_DIR}/{self.output_name}', "w")
                f.write(str(self.global_result))
                f.close()

                # Wait some seconds to make sure all clients have written the results. This will be fixed soon.
                if self.coordinator:
                    time.sleep(5)

                # Set finished flag to True, which ends the computation
                self.status_finished = True
                self.progress = "finished."
                break

            time.sleep(1)


logic = AppLogic()
