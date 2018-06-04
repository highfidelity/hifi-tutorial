//
// Sandbox/replaceAvatar.js
// 
// Author: Liv Erickson / Alan Zimmerman
// Copyright High Fidelity 2018
//
// Licensed under the Apache 2.0 License
// See accompanying license file or http://apache.org/
//
(function(){ 

    var VOLUME = 0.25;
    var chimeURL = Script.resolvePath("../sounds/confirmationChime.wav");
    var chime = SoundCache.getSound(chimeURL);

    this.replaceAvatar = function(entityID) {
        MyAvatar.useFullAvatarURL(Entities.getEntityProperties(entityID,"modelURL").modelURL);
        if (chime.downloaded) {
            Audio.playSound(chime, {
                position: MyAvatar.position,
                volume: VOLUME
            });
        }
    };
    this.replaceAvatarByMouse = function(entityID, mouseEvent) {
        if (mouseEvent.isLeftButton) {
            this.replaceAvatar(entityID);
        }
    };
    this.clickDownOnEntity = this.replaceAvatarByMouse; 
    this.startFarTrigger = this.replaceAvatar; 
    this.startNearTrigger = this.replaceAvatar; 
});