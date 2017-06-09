# sync command

To generate a `build` directory from the src directory:

`./build.py sync`

By default, the sync command will look for a `src` directory in the current working directory to build from, and put the resultant build inside of the `build` folder in the current working directory. To generate the build in a different folder, you can use the `-o` argument.

To generate a build inside of your AppData folder:

`./build.py sync -o ~/AppData/Roaming/High\ Fidelity`

When first generating a fresh build using `sync`, the models.json in the src folder will be copied to the build folder. On subsequent runs of `sync`, you will be prompted as to whether you want to copy the `models.json.gz` in the build folder to your src folder.
