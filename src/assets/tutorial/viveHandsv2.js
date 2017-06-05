Script.include("controllerDisplay.js");
Script.include("viveControllerConfiguration.js");

if (!Function.prototype.bind) {
  Function.prototype.bind = function(oThis) {
    if (typeof this !== 'function') {
      // closest thing possible to the ECMAScript 5
      // internal IsCallable function
      throw new TypeError('Function.prototype.bind - what is trying to be bound is not callable');
    }

    var aArgs   = Array.prototype.slice.call(arguments, 1),
        fToBind = this,
        fNOP    = function() {},
        fBound  = function() {
          return fToBind.apply(this instanceof fNOP
                 ? this
                 : oThis,
                 aArgs.concat(Array.prototype.slice.call(arguments)));
        };

    if (this.prototype) {
      // Function.prototype doesn't have a prototype property
      fNOP.prototype = this.prototype;
    }
    fBound.prototype = new fNOP();

    return fBound;
  };
}

function debug() {
    var args = Array.prototype.slice.call(arguments);
    args.unshift("viveHandsv2.js | ");
    print.apply(this, args);
}

var zeroPosition = { x: 0, y: 0, z: 0 };
var zeroRotation = { x: 0, y: 0, z: 0, w: 1 };

///////////////////////////////////////////////////////////////////////////////
///////////////////////////////////////////////////////////////////////////////
// Management of controller display                                          //
///////////////////////////////////////////////////////////////////////////////
ControllerDisplayManager = function() {
    var self = this;
    var controllerLeft = null;
    var controllerRight = null;
    var controllerCheckerIntervalID = null;

    this.setLeftVisible = function(visible) {
        debug("Setting left controller visible: ", controllerLeft, visible);
        if (controllerLeft) {
            debug("Controller exists, setting visibility: ", visible);
            controllerLeft.setVisible(visible);
        }
    };

    this.setRightVisible = function(visible) {
        debug("Setting right controller visible: ", controllerRight, visible);
        debug("json: ", JSON.stringify(controllerRight));
        debug("keys: ", Object.keys(controllerRight));
        if (controllerRight) {
            debug("Controller exists, setting visibility: ", visible);
            controllerRight.setVisible(visible);
        }
    };

    function updateControllers() {
        if (HMD.active) {
            if ("Vive" in Controller.Hardware) {
                if (!controllerLeft) {
                    debug("Found vive left!");
                    controllerLeft = createControllerDisplay(VIVE_CONTROLLER_CONFIGURATION_LEFT);
                }
                if (!controllerRight) {
                    debug("Found vive right!");
                    controllerRight = createControllerDisplay(VIVE_CONTROLLER_CONFIGURATION_RIGHT);
                }
                // We've found the controllers, we no longer need to look for active controllers
                if (controllerCheckerIntervalID) {
                    Script.clearInterval(controllerCheckerIntervalID);
                    controllerCheckerIntervalID = null;
                }
            } else {
                debug("HMD active, but no controllers found");
                self.deleteControllerDisplays();
                if (controllerCheckerIntervalID == null) {
                    controllerCheckerIntervalID = Script.setInterval(updateControllers, 1000);
                }
            }
        } else {
            debug("HMD inactive");
            // We aren't in HMD mode, we no longer need to look for active controllers
            if (controllerCheckerIntervalID) {
                debug("Clearing controller checker interval");
                Script.clearInterval(controllerCheckerIntervalID);
                controllerCheckerIntervalID = null;
            }
            self.deleteControllerDisplays();
        }
    }

    Messages.subscribe('Controller-Display');
    var handleMessages = function(channel, message, sender) {
        if (!controllerLeft && !controllerRight) {
            return;
        }

        if (sender === MyAvatar.sessionUUID) {
            if (channel === 'Controller-Display') {
                debug("Got controller display", channel, message);
                var data = JSON.parse(message);
                var name = data.name;
                var visible = data.visible;
                if (controllerLeft) {
                    if (name in controllerLeft.annotations) {
                        debug("Hiding controllerLeft annotation: ", name);
                        for (var i = 0; i < controllerLeft.annotations[name].length; ++i) {
                            debug("Hiding", i);
                            Overlays.editOverlay(controllerLeft.annotations[name][i], { visible: visible });
                        }
                    }
                }
                if (controllerRight) {
                    if (name in controllerRight.annotations) {
                        debug("Hiding controllerRight annotation: ", name);
                        for (var i = 0; i < controllerRight.annotations[name].length; ++i) {
                            debug("Hiding", i);
                            Overlays.editOverlay(controllerRight.annotations[name][i], { visible: visible });
                        }
                    }
                }
            } else if (channel === 'Controller-Display-Parts') {
                debug("Got display parts", channel, message);
                var data = JSON.parse(message);
                for (var name in data) {
                    var visible = data[name];
                    if (controllerLeft) {
                        controllerLeft.setPartVisible(name, visible);
                    }
                    if (controllerRight) {
                        controllerRight.setPartVisible(name, visible);
                    }
                }
            } else if (channel === 'Controller-Set-Part-Layer') {
                debug("Got set part layer", channel, message);
                var data = JSON.parse(message);
                for (var name in data) {
                    var layer = data[name];
                    if (controllerLeft) {
                        controllerLeft.setLayerForPart(name, layer);
                    }
                    if (controllerRight) {
                        controllerRight.setLayerForPart(name, layer);
                    }
                }
            } else if (channel == 'Hifi-Object-Manipulation') {
                // Disable hiding of items when equipped
                return;

                debug("Got manipulation", channel, message);

                var data = JSON.parse(message);
                var visible = data.action != 'equip';
                debug("Joint", data.joint);
                if (data.joint == "LeftHand") {
                    self.setLeftVisible(visible);
                } else if (data.joint == "RightHand") {
                    self.setRightVisible(visible);
                }
            }
        }
    }

    Messages.messageReceived.connect(handleMessages);

    this.deleteControllerDisplays = function() {
        if (controllerLeft) {
            deleteControllerDisplay(controllerLeft);
            controllerLeft = null;
        }
        if (controllerRight) {
            deleteControllerDisplay(controllerRight);
            controllerRight = null;
        }
    };

    this.destroy = function() {
        debug("Destroying controller display");
        Messages.messageReceived.disconnect(handleMessages);
        self.deleteControllerDisplays();
    };

    HMD.displayModeChanged.connect(updateControllers);

    updateControllers();
}
