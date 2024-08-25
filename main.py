import llm_query
import llm_index
import llm_test_setup
import llm_evaluator
import os


def main():
    llm_test_setup.generate_android_setup([{'name': 'Bogdan Chifor',
                                            'email': 'bogdan.chifor@tii.ae',
                                            'events': [
                                                    {'date':'08-10 10:01:23.456',
                                                    'log_level': 'I', 
                                                    'text':'MyApp1 started succesfully'},
                                                    {'date':'08-11 10:01:23.456',
                                                    'log_level': 'E', 
                                                    'text':'MyApp2 stopped because of a crash'}
                                                ]
                                            },
                                            {'name': 'Ganga Ram',
                                            'email': 'ganga.ram@tii.ae',
                                            'events': [
                                                    {'date':'08-15 10:01:23.456',
                                                    'log_level': 'I', 
                                                    'text':'MyApp3 started succesfully'},
                                                    {'date':'08-16 10:01:23.456',
                                                    'log_level': 'E', 
                                                    'text':'MyApp4 stopped because of a crash'}
                                                ]
                                            },
                                            {'name': 'John Doe',
                                            'email': 'john.doe@tii.ae',
                                            'events': [
                                                    {'date':'08-20 12:01:23.456',
                                                    'log_level': 'I', 
                                                    'text':'MyApp5 started succesfully'},
                                                    {'date':'08-21 12:01:23.456',
                                                    'log_level': 'E', 
                                                    'text':'MyApp6 stopped because of a crash'}
                                                ]
                                            },
                                        ])

    index = llm_index.LLMIndex()
    index.load_users('data/android/android_users.json')
    index.load_logcat('data/android')
    # index.load_linux_log('data/linux')
    
    querier = llm_query.LLMQuery(index)
    llm_eval = llm_evaluator.LLMEvaluator(querier)

    llm_eval.run_status_tests([
        {
            'test_id': 1,
            'query': 'Was the Android application MyApp1 running for user Bogdan on 10th of august?',
            'responses': [{
                'user': 'Bogdan',
                'application': 'myapp1',
                'status': 'running'
            }]
        },
        {
            'test_id': 2,
            'query': 'I am interested in applications MyApp1 and MyApp2 for user Bogdan. Were the applications MyApp1 runnning on 10th august and MyApp2 running on 11th August on year 2024?',
            'responses': [{
                'user': 'Bogdan',
                'application': 'myapp1',
                'status': 'running'},
                {
                'user': 'Bogdan',
                'application': 'myapp2',
                'status': 'stopped'}
            ]
        },
        {
            'test_id': 3,
            'query': 'Was MyApp1 running for Ganga on 15 aug?',
            'responses': [{
                'user': 'Ganga',
                'application': 'myapp1',
                'status': 'stopped'}
            ]
        },
        {
            'test_id': 4,
            'query': 'What Android app was used by Doe on 20 Aug and what was the app status?',
            'responses': [{
                'user': 'Doe',
                'application': 'myapp5',
                'status': 'running'}
            ]
        },
        {
            'test_id': 5,
            'query': 'Was MyApp5 used by user John on 20 Aug and what was the status? What about user Chifor with MyApp1 on 10 Aug and user Ram with MyApp3 on 15 aug?',
            'responses': [{
                'user': 'John',
                'application': 'myapp5',
                'status': 'running'},
                {
                'user': 'Chifor',
                'application': 'myapp1',
                'status': 'running'},
                {
                'user': 'Ram',
                'application': 'myapp3',
                'status': 'running'}
            ]
        },
    ])

if __name__ == "__main__":
    main()
