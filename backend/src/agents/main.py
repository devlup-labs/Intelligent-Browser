from crew import PlannerCrew
import json
from examples.planner_agent_example import planner_examples_list

# existing list 
user_request=input("Ask me anything!! ---> ")

# imp that it be a string since used in description
agent_list=["Chat","Browser","Computer","File"]

example_list_json=json.dumps(planner_examples_list,indent=2)
# print(example_list_json)

def run():
    inputs = {
        "user_request":user_request,
        "agents_list":agent_list,
        "examples_list":example_list_json,
    }

    result=PlannerCrew().crew().kickoff(inputs=inputs)
    print(result)


if(__name__=="__main__"):
    run()



