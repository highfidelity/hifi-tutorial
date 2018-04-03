//
// Sandbox/zoneItemMovement.js
// 
// Author: Liv Erickson
// Copyright High Fidelity 2018
//
// Licensed under the Apache 2.0 License
// See accompanying license file or http://apache.org/
//
(function(){

    var DESKTOP_IDENTIFIER = "-Desktop";
    var GAMEPAD_IDENTIFIER = "-Gamepad";
    var VIVE_IDENTIFIER = "-Vive";
    var RIFT_IDENTIFIER = "-Rift";
  
    var GIF_DESKTOP_URL = "https://giphy.com/gifs/LYJZ2YTQiY0WoSoOKj/html5";
    var GIF_VIVE_URL = "https://giphy.com/gifs/mnqTywAN88tiJarYIS/html5";
    var GIF_RIFT_URL = "https://giphy.com/gifs/mnqTywAN88tiJarYIS/html5";
    var GIF_GAMEPAD_URL = "https://giphy.com/gifs/LYJZ2YTQiY0WoSoOKj/html5";

    var WEB_OVERLAY_BASE_PROPERTIES = {
        "dimensions" : { "x": 3.200000047683716, "y": 1.7999999523162842, "z": 0.009999999776482582 },
        "position" : {"x" : 3.3181, "y" : -8.6590, "z" : -0.2557},
        "rotation" : { "w": 0.7660241723060608, "x": -0.0002027750015258789,"y": -0.6427602767944336, "z": 0}
    };

    var SOUND_URL = 'atp:/sounds/MovementAudio.wav';
    var SOUND = SoundCache.getSound(SOUND_URL);

    var position;
    var audioPlaying;

    var desktopEntities = [];
    var gamePadEntities = [];
    var viveEntities = [];
    var riftEntities = [];
    var webGifOverlay;

    var wantDebug = false;

    var ZoneItem = function(){

    };

    var makeVisible = function(entity) {
        Entities.editEntity(entity, { visible: true });
    };

    var makeInvisible = function(entity) {
        Entities.editEntity(entity, { visible: false });
    };

    var showPanelsForDesktop = function() {
        var webOverlayProperties = WEB_OVERLAY_BASE_PROPERTIES;
        if (!(typeof(Controller.Hardware.GamePad) === 'undefined')) {
            // We have a game pad
            desktopEntities.forEach(function(element) {
                if (wantDebug) {
                    print("Showing desktop entities");
                }
                makeVisible(element);
            });
            gamePadEntities.forEach(function(element) {
                if (wantDebug) {
                    print("Showing game pad entities");
                }
                makeVisible(element);
            });
            webOverlayProperties.url = GIF_GAMEPAD_URL;
            webGifOverlay = Overlays.addOverlay(WEB_OVERLAY_BASE_PROPERTIES);
        } else {
            desktopEntities.forEach(function(element) {
                if (wantDebug) {
                    print("Showing only desktop entities");
                }
                makeVisible(element);
            });
            webOverlayProperties.url = GIF_DESKTOP_URL;
            webGifOverlay = Overlays.addOverlay('web3d', webOverlayProperties);
        }
    };

    var showPanelsForVR = function(deviceType) {
        var webOverlayProperties = WEB_OVERLAY_BASE_PROPERTIES;
        switch (deviceType) {
            case "Rift" :
                if (!(typeof(Controller.Hardware.GamePad) === 'undefined')) {
                    if (wantDebug) {
                        print("Showing Gamepad entities for Rift");
                    }
                    gamePadEntities.forEach(function(element) {
                        makeVisible(element);
                    });
                    webOverlayProperties.url = GIF_GAMEPAD_URL;
                    webGifOverlay = Overlays.addOverlay('web3d', webOverlayProperties);                 
                } else {
                    if (wantDebug) {
                        print("Showing Rift hand controller entities");
                    }
                    riftEntities.forEach(function(element) {
                        makeVisible(element);
                    });
                    webOverlayProperties.url = GIF_RIFT_URL;
                    webGifOverlay = Overlays.addOverlay('web3d', webOverlayProperties);      
                }
                break;
            default:
            // Assume hand controllers are present for OpenVR devices
                if (wantDebug) {
                    print("Showing hand controller entities for Vive");
                }
                viveEntities.forEach(function(element) {
                    makeVisible(element);
                });
                webOverlayProperties.url = GIF_VIVE_URL;
                webGifOverlay = Overlays.addOverlay('web3d', webOverlayProperties);      

        } 
    };

    var setDisplayType = function() {
        if (!HMD.active) {
            // Desktop mode, because not in VR
            showPanelsForDesktop();
        } else {
            var deviceType = HMD.isHMDAvailable("Oculus Rift") ? "Rift" : "Vive";
            showPanelsForVR(deviceType);
        }
    };

    var hideAllElements = function() {
        desktopEntities.forEach(function(element) {
            makeInvisible(element);
        });

        viveEntities.forEach(function(element) {
            makeInvisible(element);
        });

        gamePadEntities.forEach(function(element) {
            makeInvisible(element);
        });

        riftEntities.forEach(function(element) {
            makeInvisible(element);
        });
        Overlays.deleteOverlay(webGifOverlay);
        webGifOverlay = "";
    };

    ZoneItem.prototype = {
        preload: function(entityID) {
            position = Entities.getEntityProperties(entityID, 'position').position;
        },
        enterEntity: function() {
            var nearbyEntities = Entities.findEntities(position, 10);
            nearbyEntities.forEach(function(element) {
                var elementName = Entities.getEntityProperties(element, 'name').name;
                if (wantDebug) {
                    print ("Found entity with name: " + elementName);
                }
                if (elementName.indexOf(DESKTOP_IDENTIFIER) !== -1) {
                    desktopEntities.push(element);
                    if (wantDebug) {
                        print("Added" + element + " to desktop");
                    }
                } else if (elementName.indexOf(GAMEPAD_IDENTIFIER) !== -1) {
                    gamePadEntities.push(element);
                    if (wantDebug) {
                        print("Added" + element + " to gamepad");
                    }
                } else if (elementName.indexOf(VIVE_IDENTIFIER) !== -1) {
                    viveEntities.push(element);
                    if (wantDebug) {
                        print("Added" + element + " to vive");
                    }
                } else if (elementName.indexOf(RIFT_IDENTIFIER) !== -1) {
                    riftEntities.push(element);
                    if (wantDebug) {
                        print("Added" + element + " to rift");
                    }
                }
            });
            setDisplayType();
            if (SOUND.downloaded) {
                audioPlaying = Audio.playSound(SOUND, {
                    position: MyAvatar.position,
                    volume: 1.0,
                    localOnly: true
                });
            }
            
        },
        leaveEntity: function() {
            hideAllElements();
            if (audioPlaying) {
                audioPlaying.stop();
            }
        }
    };

    return new ZoneItem();
});