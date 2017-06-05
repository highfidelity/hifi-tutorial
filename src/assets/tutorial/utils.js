//
//  utils.js
//
//  Created by Ryan Huffman on 9/1/16.
//  Copyright 2016 High Fidelity, Inc.
//
//  Distributed under the Apache License, Version 2.0.
//  See the accompanying file LICENSE or http://www.apache.org/licenses/LICENSE-2.0.html
//

Utils = {
    findEntity: function(properties, searchRadius, filterFn) {
        var entities = findEntities(properties, searchRadius, filterFn);
        return entities.length > 0 ? entities[0] : null;
    },

    // Return all entities with properties `properties` within radius `searchRadius`
    findEntities: function(properties, searchRadius, filterFn) {
        if (!filterFn) {
            filterFn = function(properties, key, value) {
                return value == properties[key];
            }
        }
        searchRadius = searchRadius ? searchRadius : 100000;
        var entities = Entities.findEntities({ x: 0, y: 0, z: 0 }, searchRadius);
        var matchedEntities = [];
        var keys = Object.keys(properties);
        for (var i = 0; i < entities.length; ++i) {
            var match = true;
            var candidateProperties = Entities.getEntityProperties(entities[i], keys);
            for (var key in properties) {
                if (!filterFn(properties, key, candidateProperties[key])) {
                    // This isn't a match, move to next entity
                    match = false;
                    break;
                }
            }
            if (match) {
                matchedEntities.push(entities[i]);
            }
        }

        return matchedEntities;
    }
};
