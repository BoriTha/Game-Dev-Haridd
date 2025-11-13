"""
Level data structures for multi-room dungeon generation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class LevelData:
    """
    Represents a complete multi-room level.
    
    Attributes:
        rooms: Dictionary mapping room IDs to room data
        internal_graph: Adjacency list of room connections
        start_room_id: ID of the starting room
        goal_room_id: ID of the final/goal room
    """
    rooms: Dict[str, Any] = field(default_factory=dict)
    internal_graph: Dict[str, List[str]] = field(default_factory=dict)
    start_room_id: Optional[str] = None
    goal_room_id: Optional[str] = None
    
    def get_room(self, room_id: str) -> Optional[Any]:
        """Get room by ID."""
        return self.rooms.get(room_id)
    
    def add_room(self, room_id: str, room: Any) -> None:
        """Add a room to the level."""
        self.rooms[room_id] = room
        if room_id not in self.internal_graph:
            self.internal_graph[room_id] = []
    
    def connect_rooms(self, from_id: str, to_id: str) -> None:
        """Create a directed edge in the room graph."""
        if from_id in self.internal_graph:
            if to_id not in self.internal_graph[from_id]:
                self.internal_graph[from_id].append(to_id)
        else:
            self.internal_graph[from_id] = [to_id]
    
    def get_path_to_goal(self) -> Optional[List[str]]:
        """
        Find path from start_room_id to goal_room_id using BFS.
        
        Returns:
            List of room IDs forming the path, or None if no path exists
        """
        if not self.start_room_id or not self.goal_room_id:
            return None
        
        # BFS
        queue = [(self.start_room_id, [self.start_room_id])]
        visited = {self.start_room_id}
        
        while queue:
            current_id, path = queue.pop(0)
            
            if current_id == self.goal_room_id:
                return path
            
            for neighbor_id in self.internal_graph.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        return None  # No path found
    
    def get_room_depth(self, room_id: str) -> int:
        """
        Calculate depth (distance from start) for a room.
        
        Returns:
            Depth value, or -1 if room not reachable from start
        """
        if not self.start_room_id or room_id not in self.internal_graph:
            return -1
        
        # BFS to find shortest distance
        queue = [(self.start_room_id, 0)]
        visited = {self.start_room_id}
        
        while queue:
            current_id, depth = queue.pop(0)
            
            if current_id == room_id:
                return depth
            
            for neighbor_id in self.internal_graph.get(current_id, []):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, depth + 1))
        
        return -1  # Not reachable


@dataclass
class LevelGenerationConfig:
    """
    Configuration for multi-room level generation.
    
    Attributes:
        num_rooms: Total number of rooms in level
        layout_type: Type of level layout ("linear", "branching", "looping")
        branch_probability: Chance of creating branches (for branching layout)
        loop_probability: Chance of creating loops (for looping layout)
        entrance_doors_per_room: Number of entrance doors per room
        exit_doors_per_room: Number of exit doors per room
    """
    num_rooms: int = 5
    layout_type: str = "linear"  # "linear", "branching", "looping"
    branch_probability: float = 0.3
    loop_probability: float = 0.2
    entrance_doors_per_room: int = 1  # Number of entrance doors
    exit_doors_per_room: int = 1     # Number of exit doors
