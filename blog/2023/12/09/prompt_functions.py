import re
from openai import OpenAI
client = OpenAI()

def get_response(msg, mod="gpt-3.5-turbo", temp=0):
    response = client.chat.completions.create(
      model=mod,
      messages=msg,
      temperature=temp
    )
    return response.choices[0].message.content


def clean_answer(answer):
    # Remove everything but numbers in integer or decimal form
    answer_clean = re.sub('[^\d\.]', '', answer)
    # If the last character is a decimal, remove it, it was probably presented as a sentence
    if answer_clean[-1] == '.':
        answer_clean = answer_clean[:-1]    
    # If number contains decimal, decide if it should be removed
    if '.' in answer_clean:
        # If the number contains only trailing zeroes, strip them and remove it
        if answer_clean[-1] == '0' and answer_clean[-2] == '0':
            answer_clean = answer_clean.rstrip('0')
            answer_clean = answer_clean[:-1]
        # If the decimal is now the last character, remove it
        if answer_clean[-1] == '.':
            answer_clean = answer_clean[:-1]
    return answer_clean


def identify_final_answer(solution):
    instructions = '''
      You will be provided with the solution to a math problem,
      delimited by triple backticks.
    
      Return the final answer, expressed as a single number, 
      prefixed by 'Final answer:'
    '''
    user_content = f'```{solution}```'
    msg = [
      {"role": "system", "content": instructions},
      {"role": "user", "content": user_content}
    ]
    response = get_response(msg=msg, temp=0)
    try: # Try to extract the answer using the prefix
      answer = response.split('Final answer: ')[1]
      return clean_answer(answer)
    except:
      return response


def baseline_solver(question):
    instructions = "Solve the math problem delimited by triple backticks."
    user_content = f"```{question}```\nLet's work this out in a step by step way to be sure we have the right answer"
    msg = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_content}
    ]
    solution = get_response(msg=msg, temp=0.5)
    answer = identify_final_answer(solution)
    return {
      'is_correct': answer == '3',
      'solution': solution,
      'question': question,
      'answer': answer
    }


def step_generator(solutions):
    instructions = '''
      You're given three different solutions to a single math problem, delimited by
      triple hashtags. Synthesize the solutions into a final set of steps to solve
      the problem. Remove any calculations from the instructions, leaving only the
      steps.
    '''
    user_content = f'''
      ###
      Solution 1: 
      {solutions[0]}
      ---
      
      Solution 2: 
      {solutions[1]}
      ---
      
      Solution 3: 
      {solutions[2]}
      ###
      
      Synthesize the three solutions above. Remove any calculations from the 
      instructions, leaving only the steps.
    '''
    msg = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_content}
    ]
    return get_response(msg=msg, temp=0.3)


def stepwise_solver(question, steps):
    instructions = "Solve the math problem in triple backticks, using the steps provided in triple hashtags."
    user_content = f"```{question}```\n\n###{steps}###"
    msg = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": user_content}
    ]
    solution = get_response(msg=msg, temp=0.5)
    answer = identify_final_answer(solution)
    return {
      'is_correct': answer == '3',
      'solution': solution,
      'question': question,
      'steps': steps,
      'answer': answer
    }
