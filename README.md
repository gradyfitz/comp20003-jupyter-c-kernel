# Minimal C kernel for Jupyter with COMP20003 Customisation

## Use with Docker (recommended)

 * `docker pull gradyfitz/comp20003-jupyter-c-kernel:latest`
 * `docker run -p 8888:8888 --cap-add SYS_PTRACE --security-opt seccomp=unconfined gradyfitz/comp20003-jupyter-c-kernel:latest`
 * Copy the given URL containing the token, and browse to it. For instance:
 
 ```
 Copy/paste this URL into your browser when you connect for the first time,
 to login with a token:
    http://localhost:8888/?token=66750c80bd0788f6ba15760aadz53beb9a9fb4cf8ac15ce8
 ```

 * Upload all the notebook images to your server using the upload button and 
 clicking the upload button for each file. As long as you continue to use the 
 same docker image (you can check its name using docker ps -a), 
 your files should persist, though you might want to verify this is the case on 
 your system before trusting it.
 
 * You can shut down the server by using 
 ```bash
 docker stop <machine name>
 ```
 
 * You can bring the server back up by using
 ```bash
 docker start <machine name>
 ```
 
 * As before, you can check the list of environments you have in docker using
 ```bash
 docker ps -a
 ```
 
 * NOTE: Due to some issues somewhere, on Windows you will have to restart 
 docker after every time you restart your computer. This may be slightly 
 annoying, but hopefully shouldn't cause too much trouble, I'll be keeping an 
 eye out for a proper fix, either way.
 
 To explain a few things about the run command:
 
 * **SYS_PTRACE** allows a number of compiling directives to work, so it is 
	important that it be specified as a capability of the docker.
 * **security-opt seccomp=unconfined** turns off a few security-related system
    calls, we need this to be able to remove adress space randomisation. The 
	default profile is probably mostly fine, but if you want to use this outward
	facing, you would want to take the default security profile 
	https://github.com/moby/moby/blob/master/profiles/seccomp/default.json
	and add the personality system call to the allowed system call list when
	you run the system, as explained in
	https://docs.docker.com/engine/security/seccomp/#pass-a-profile-for-a-container
	

## Manual installation

Works only on Linux and OS X. Windows is not supported yet. If you want to use this project on Windows, please use Docker.


 * Make sure you have the following requirements installed:
  * gcc
  * jupyter
  * python 3
  * pip

### Step-by-step:
 * `pip install jupyter-c-kernel`
 * `install_c_kernel`
 * `jupyter-notebook`. Enjoy!

## Example of notebook

![Example of notebook](example-notebook.png?raw=true "Example of notebook")

## Custom compilation flags

You can use custom compilation flags like so:

![Custom compulation flag](custom_flags.png?raw=true "Example of notebook using custom compilation flags")

Here, the `-lm` flag is passed so you can use the math library.

## Contributing

You can use docker cp to make changes to the kernel on the live machine. If you
would like to get at the source yourself, consider working on Breandan Rius' 
image.

The docker image installs the kernel in editable mode, meaning that you can
change the code in real-time in Docker. For that, just run the docker box like
that:

```bash
git clone https://github.com/brendan-rius/jupyter-c-kernel.git
cd jupyter-c-kernel
docker run -v $(pwd):/jupyter/jupyter_c_kernel/ -p 8888:8888 brendanrius/jupyter-c-kernel
```

This clones the source, run the kernel, and binds the current folder (the one
you just cloned) to the corresponding folder in Docker.
Now, if you change the source, it will be reflected in [http://localhost:8888](http://localhost:8888)
instantly. Do not forget to click "restart" the kernel on the page as it does
not auto-restart.

## License

[MIT](LICENSE.txt)
