# anteater-test


* Setup the python environment in the current working directory for broken.py:
Create virtual environment env, activate the environment and install the networkx and pydot packages into the activated env virtual environment.

```
>> python3 -m venv env
>> source env/bin/activate
(env) >> pip3 install networkx==2.4
(env) >> pip3 install pydot==1.4.1

```

* Make sure the mpi log files and communicationCoefficients file are in the current working directory of broken.py

* Run broken.py

```
python3 broken.py 4

```

* broken.py generates the following task graph image:
```
dotOutput.png
```

### notes

Checkout folders bug_1 and bug_2 to see the two scenarios where the broken.py code fails.
* In each folder app.c is the C file that generated the MPI log files.
* wrong.png is the wrong output generated by broken.py
* correct.png is the expected output to be generated by broken.py
* mpi_rank_*.txt are the mpi log files read by broken.py
* communicationCoefficients is a text file required by broken.py

### source credits
The bug is originally in one of the python's networkx package functions and the function that calls the networkx function that was pulled into broken.py manually to fix the bug. As of today bug still seems to exist in the networkx package: 
https://networkx.github.io/documentation/stable/_modules/networkx/algorithms/dag.html#dag_longest_path
