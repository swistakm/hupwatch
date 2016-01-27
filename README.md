# hupwatch
Simple utility for graceful reloading of services.

General usage bases on my other project 
[ianitor](https://github.com/ClearcodeHQ/ianitor). **hupwatch** simple shell
command that wraps process and can be simply used in your existing
process/service supervision tool like [supervisord](http://supervisord.org/), 
[circus](http://circus.readthedocs.org/en/0.11.1/),
[runit](http://smarden.org/runit/) etc.


## why?

Graceful reloading of web applications today is a must. Almost every DevOps 
should tell you that.
Many Python web servers allow such scenario but handle this differently.
In most cases you end up with two options:
* [gunicorn](https://github.com/benoitc/gunicorn) allows to do this by simply
  sending Unix `HUP` signal to the gunicorn process. It will gracefully stop
  existing workers and start new ones with new version of code. Other choice
  is to send `USR2` signal that will spawn new master gunicorn process with
  set of udpated workers. You are then able to 
* [uWSGI](https://github.com/unbit/uwsgi) gives few options and the best one is
  very similar in effect to sending `USR2` to `gunicorn`. uWSGI provides 
  very verbose documentation on that. One could say "too verbore". Good luck
  on understanding it!
* You may depend on load balancing on higher level of architecture abstraction.
  Still you need to be able to finish current requests that are being processed
  during the deployment so you require a web server that can gracefully 
  shutdown.

Greceful reloading implementations provided by gunicorn and uWSGI are both neat
but fail in reality when you try to automate things or use any of popular tools 
for process supervision:

* Gunicorn's HUP-reload will fail if you switch your codebase using symlinks.
  This is a very popular technique in many organizations. And also it will
  not update gunicorn configuration but only restart workers with a new code.
  This will work fine if you simply replace the code *in situ* but good luck
  with that if you use Django and did a lot of updates to templates with
  you current release. Old gunicorn workers will "gracefuly" shutdown but may
  also "gracefully" respond with server errors if you replaced code in place.
  Gunicorn accepts a `--chdir` argument that should fix that but it again does
  not play well with some deploment solutions like buildout.
* The second approach (spewning new master server process) seems better and
  generally works well with symlinks but does not play well with many process 
  supervision tools. The most popular one in Python world - supervisord - must 
  spawn a subprocess by itself in order to be able to control it. Once gunicorn 
  (after `USR2` signal) or uWSGI (after whatever it requires) spawns (re-execs) 
  a new master process it has no longer the supervisor as its parent. In short,
  it will eventually become the child process of `init` and there is no way to 
  "adopt" such process by supervisor. Supervisor will try to spawn it again and
  you end up with twice more workers than you expected. If you won't notice the 
  issue or cleanup this mess you may run out of resources.

You may work around these issues by providing some custom integration for 
whatever process supervision tool you are using or do some crazy next/current
instance switching and mantain doubled configuration of services only for this
single purpose. This will make your solution either non-portable to other 
tools or make the whole solution harder to automate in a reliable way.


## how does it work?

**hupwatch** provides a single solution that can be easily integrated with 
virtually any supervision tool and allows to reload whole web servers with only
single command that is available on any POSIX system: `kill`

    # on terminal or inside supervisord config:
    hupwatch -- gunicorn myapp:application --bind unix:/tmp/myapp.sock
    
    # on any other terminal:
    kill -HUP <hupwatch_pid>
    
**hupwatch** will start anything that you have provided after the `--`
characters as its own subprocess (using `subprocess.Popen()`) and listens for 
incoming Unix signals. Whenever it gets a `HUP` signal it starts a new process 
with the same arguments and sends `TERM` signal to the process that was started
previously so it can shutdown gracefuly.

If you paid attentions this requires only two things to make it working as
a solution for graceful reload:

* you need to use Unix sockets instead of ports so both old and new processes 
  can bind to the same address
* your web server needs to perform a graceful shutdown when it receives `TERM` 
  signal. Gunicorn already does that. uWSGI is not supported yet.


## anything else?

See the usage with `hupwatch --help` for more information on possible 
configuration options.

There is also some details important detail of handling failures 
and what to do when **hupwatch** receives other signals (e.g. `KILL`, `TERM`, 
`INT`). By default it assumes that you want to have have your process working 
no matter what happens with the parent (hupwatch). So in case of failure it 
leaves it as it is - spawned process will become a child of `init`. If you 
that this happened you can clean up the mess manually without interrupting the
process of serving web requests. This behaviour can be changed with 
`--kill-at-exit` flag.
