import environ


@environ.config
class Config:
    target_domain = environ.var('https://osugidani.jp')
    local_domain = environ.var('https://i.sg.ndxk.cc')
    port = environ.var(5000, converter=int)
    skip_ascii = environ.bool_var(True)


AppConfig = Config.from_environ()
