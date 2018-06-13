//
// movementToggle.js
// 
// Author: Liv Erickson
// Copyright High Fidelity 2018
//
// Licensed under the Apache 2.0 License
// See accompanying license file or http://apache.org/
//
(function(){
  
    var ENABLED_TEXTURE = Script.resolvePath("../textures/advmove_Trigger_Off.texmeta.json");
    var DISABLED_TEXTURE = Script.resolvePath("../textures/advmove_Trigger_On.texmeta.json");

    var TIMEOUT = 1000;
    
    var isActive;
    var canChange = true;
    var _entityID;
    
   
    var AdvancedMovementToggle = function() {
    
    };
    
    var switchControlMechanics = function() {
        // avoid duplicate events
        isActive = !isActive;
        MyAvatar.useAdvancedMovementControls = isActive;
        switchSignTexture(isActive);
    };

    var switchSignTexture = function(enabled) {
        Entities.editEntity(_entityID, {
            "textures" : JSON.stringify({"file1" : enabled ? ENABLED_TEXTURE : DISABLED_TEXTURE})
        });
    };
    
    AdvancedMovementToggle.prototype = {
        preload : function(entityID) {
            _entityID = entityID;
            isActive = MyAvatar.useAdvancedMovementControls;
            switchSignTexture(isActive);
        },
        mousePressOnEntity : function() {
            if (canChange){ 
                canChange = false;
                switchControlMechanics();
                Script.setTimeout(function(){
                    canChange = true;
                }, TIMEOUT);
            }
        }
    };
    
    return new AdvancedMovementToggle();

});
