General Debugging Guide for HarmoniQ Web Application
===================================================

This document provides troubleshooting steps, commands, and useful information for debugging the HarmoniQ web application.

1. Handling the "Address already in use" Error

----------------------------------------------

If you encounter the following error during the application startup:

    [Errno 48] Address already in use


This means that the port you are trying to use is already occupied by another process. To fix this, you should restart the application with a different port.

### Solution:
To start the application on a new port, use the following command:

.. code-block:: bash

    launch-app --debug --port ####

Replace `####` with the desired port number (e.g., 5001, 5002, etc.).
You can also check which process is using the port with the following command:

.. code-block:: bash

    lsof -i :<port_number>


2. FastAPI Information on the Website
------------------------------------

After launching the application, you can access the FastAPI documentation and interact with the API manually. This is a valuable tool for debugging and executing specific methods.

To access the FastAPI documentation, visit the following URL:

.. code-block:: bash

    http://0.0.0.0:####/docs

Replace `####` with the port number you used to launch the application (e.g., 5000, 5001, etc.).


This FastAPI interface allows you to:
- View all available endpoints and their parameters
- Manually execute methods and inspect responses
- Test specific API calls directly from the browser interface

3. Command-Line Help Methods
----------------------------

In case you need more information about how to use specific commands, here are some useful command-line help methods.

### a. Initializing the Database (`init-db`)
To initialize the database or perform operations such as resetting, filling, or populating it, you can use the `init-db` command.

To see the help for the `init-db` command, run:

.. code-block:: bash

    init-db -h


This will display the following usage options:

.. code-block:: bash

    usage: init-db [-h] [-t] [-R] [-f] [-p]

    Initialise la base de données

    options:
      -h, --help     Affiche ce message d'aide et quitte
      -t, --test     Utilise la base de données de test
      -R, --reset    Réinitialise la base de données
      -f, --fill     Remplit la base de données si elle est vide
      -p, --populate Remplit la base de données avec des données de référence



### Example:
To initialize the database with test data, use:

.. code-block:: bash

    init-db -t


This will set up the database with predefined test data.

### b. Launching the App (`launch-app`)
To start the HarmoniQ web application, use the `launch-app` command. You can also specify options like `--debug`, `--host`, and `--port` to customize the startup process.

To view the help message for the `launch-app` command, run:

.. code-block:: bash

    launch-app -h

This will display the following usage options:

.. code-block:: bash

    usage: launch-app [-h] [--debug] [--host HOST] [--port PORT]

    Launch the web interface

    options:
      -h, --help     Show this help message and exit
      --debug        Enable debug mode
      --host HOST    Server IP address
      --port PORT    Server port

### Example:
To launch the application in debug mode on port 5001, use:

.. code-block:: bash

    launch-app --debug --port 5001

This will start the application with debugging enabled, allowing you to see detailed error messages and logs in the console.
