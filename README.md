# hupwatch
Simple utility for graceful reloading of services.

General usage bases on my other project 
[ianitor](https://github.com/ClearcodeHQ/ianitor). **hupwatch** is a simple
shell command that wraps process and can be simply used in your existing
process/service supervision tool like [supervisord](http://supervisord.org/), 
[circus](http://circus.readthedocs.org/en/0.11.1/),
[runit](http://smarden.org/runit/) etc.


## why?

Reloading of web application code gracefully is a today's must. Every DevOps
should tell you that already. Many of Python web servers allow such scenario
but handle this differently. Usually you end up with only few reasonable
options:

* [gunicorn](https://github.com/benoitc/gunicorn) allows to do this by simply
  sending Unix `HUP` signal to the gunicorn process. It will gracefully stop
  existing workers and start new ones with new version of code. Other choice
  is to send `USR2` signal that will spawn new master gunicorn process with
  set of udpated workers. You are then able to
* [uWSGI](https://github.com/unbit/uwsgi) gives few options and the best one is
  very similar in effect to sending `USR2` to `gunicorn`. uWSGI provides
  very verbose documentation on that. One could say "too verbore". Good luck
  on understanding it!
* You may depend on load balancing on the higher level your architecture stack.
  Still you need to be able to finish current requests that are being processed
  during the deployment. So you require a web server that can at least
  gracefully shutdown its workers.

Graceful reloading implementations provided by gunicorn and uWSGI are both neat
but fail in reality when you try to automate things or use it with any of
the popular tools for process/service supervision:

* Gunicorn's HUP-reload will fail if you switch your codebase using symlinks.
  This is a very popular technique in many organizations. Gunicorn will also
  it will not update gunicorn its own configuration on `HUP` but will only
  restart workers with a new code. This approach will work fine if you simply
  replace the code *in situ* and do not need to tune configuration options like
  worker class or concurrency settings. Still, I wish you a good luck
  with that if you use Django and you did a lot of updates to templates with
  your latest release. Old gunicorn workers will "gracefuly" shutdown but may
  also "gracefully" respond with server errors if you replaced code in place.
  Gunicorn accepts a `--chdir` argument that should fix that but it again does
  not play well with some popular deploment solutions like buildout.
* The second approach (spawning new master server process) seems to be a better
  way and generally works well with symlinks but does not play well with many
  process supervision tools. The most popular one in Python world - supervisord - must
  spawn a subprocess by itself in order to be able to control it. Once gunicorn 
  (after `USR2` signal) or uWSGI (after whatever it requires) spawns (re-execs) 
  a new master process it has no longer the supervisor as its parent. In short,
  it will eventually become the child process of `init` and there is no way to 
  "adopt" such process by supervisor. Supervisor will try to spawn it again and
  you end up with twice more workers than you expected. If you won't notice that
  and perform many subsequent reloads in that manner you may eventually run out
  of resources.
* Generally handling updates with the help of load balancer seems like a safer
  solution because you can simply restart web servers once they are removed
  from your stack. This is unfortunately a lot harder to automate and adds
  additional level of complexity to your whole operations.

You may of course work around these issues by providing some custom integration
for whatever process supervision tool you are using or do some crazy
next/current instance switching and mantain doubled configuration of services
only for this single purpose. This will make your solution either non-portable
to other tools or make the whole solution harder to automate in a reliable way.


## how does it work?

**hupwatch** provides a single solution that can be easily integrated with 
virtually any supervision tool and allows to reload whole web servers with only
single command that is available on any POSIX system. It is `kill`:

    # on terminal or inside supervisord config:
    $ hupwatch -- gunicorn myapp:application --bind unix:/tmp/myapp.sock
    => HUP watch [INFO    ]: Starting HUP watch (92808)
    => HUP watch [INFO    ]: Child process 92809 started
    => HUP watch [INFO    ]: Pausing for signal
    [2016-01-27 17:24:13 +0100] [92809] [INFO] Starting gunicorn 19.4.5
    [2016-01-27 17:24:13 +0100] [92809] [INFO] Listening at: unix:/tmp/myapp.sock (92809)
    [2016-01-27 17:24:13 +0100] [92809] [INFO] Using worker: sync
    [2016-01-27 17:24:13 +0100] [92812] [INFO] Booting worker with pid: 92812

    # issued on any other terminal:
    kill -HUP <hupwatch_pid>
    
    # continued result in the hupwatch stdout:
    [...]
    => HUP watch [DEBUG   ]: HUP: >>>
    => HUP watch [DEBUG   ]: HUP: Waiting for process (92955) to warm up
    => HUP watch [DEBUG   ]: HUP: Sending SIGTERM to old process (92809)
    => HUP watch [DEBUG   ]: HUP: Waiting for process (92809) to quit...
    [2016-01-27 17:24:46 +0100] [92809] [INFO] Handling signal: term
    [2016-01-27 17:24:46 +0100] [92955] [INFO] Starting gunicorn 19.4.5
    [2016-01-27 17:24:46 +0100] [92955] [INFO] Listening at: unix:/tmp/myapp.sock (92955)
    [2016-01-27 17:24:46 +0100] [92955] [INFO] Using worker: sync
    [2016-01-27 17:24:46 +0100] [92964] [INFO] Booting worker with pid: 92964
    [2016-01-27 17:24:58 +0100] [92812] [INFO] Worker exiting (pid: 92812)
    [2016-01-27 17:24:58 +0100] [92809] [INFO] Shutting down: Master
    => HUP watch [DEBUG   ]: CHLD: >>>
    => HUP watch [INFO    ]: CHLD: Child process quit
    => HUP watch [DEBUG   ]: CHLD: <<<
    => HUP watch [INFO    ]: HUP: Old process quit with code: 0
    => HUP watch [DEBUG   ]: HUP: <<<
    => HUP watch [INFO    ]: Pausing for signal

**hupwatch** will start anything that you have provided after the `--`
characters as its own subprocess (using `subprocess.Popen()`) and listens for
incoming Unix signals. Whenever it gets a `HUP` signal it starts a new process
with the same arguments and sends `TERM` signal to the process that was started
previously so it can shutdown gracefuly.

This make the whole realoading process very easy to automate. No need to
execute multiple commands and mantain any state between them. Simply HUP'n'go!
This is a good news for [fabric](https://github.com/fabric/fabric) enthusiasts -
don't need to worry about lost shh connection during whole reload procedure
because it takes only one step (at least if you use symlinks). There is nothing
to interrupt!

Rolling back the update is also painless: simply change project symlink and
issue another `HUP` signal to the same hupwatch pid. Auto rollback should be
also easy to implement and we are open to any contributions!

If you paid attention then you should already notice that this requires only
two things to make it working as a solution for graceful reload:

* You need to use Unix sockets instead of ports so both old and new processes
  can bind to the same address
* Your web server needs to perform a graceful shutdown when it receives `TERM`
  signal. Gunicorn already does that. uWSGI is not supported yet.


## anything else?

See the usage with `hupwatch --help` for more information on possible
configuration options:


There is also some details important detail of handling failures
and what to do when **hupwatch** receives other signals (e.g. `KILL`, `TERM`,
`INT`). By default it assumes that you want to have have your process working
no matter what happens with the parent (hupwatch). So in case of failure it
leaves it as it is - spawned process will become a child of `init`. If you
that this happened you can clean up the mess manually without interrupting the
process of serving web requests. This behaviour can be changed with
`--kill-at-exit` flag.


## status of this project?

This is more a proof of concept than a battle-tested tool. Anyway, there are
only few lines of code that actually do any work. Most of the code in this
package is extensive logging and parsing of arguments.
This state of this package will eventually change in a near future, because
it solves a real problem that we have in my organization.
So give it a try at least in your staging/testing environment.

Contributions are really welcome!
