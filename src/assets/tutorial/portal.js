(function(){
    var portalDestination;

    this.preload = function(entityID) {
        var properties = Entities.getEntityProperties(entityID);
        portalDestination = properties.userData;

        print("portal.js | The portal destination is " + portalDestination);
    }

    this.enterEntity = function(entityID) {
        print("portal.js | enterEntity");

        var properties = Entities.getEntityProperties(entityID); // in case the userData/portalURL has changed
        portalDestination = properties.userData;

        print("portal.js | enterEntity() .... The portal destination is " + portalDestination);

        if (portalDestination.length > 0) {
            if (portalDestination[0] == '/') {
                print("Teleporting to " + portalDestination);
                Window.location = portalDestination;
            } else {
                print("Teleporting to hifi://" + portalDestination);
                Window.location = "hifi://" + portalDestination;
            }
        }

    };

    this.leaveEntity = function(entityID) {
        print("portal.js | leaveEntity");
    };
})
