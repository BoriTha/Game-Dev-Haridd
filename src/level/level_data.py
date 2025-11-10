"""
Level data structures for multi-room dungeon generation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from src.level.room_data import RoomData


@dataclass
class DoorLink:
    """
    Represents a connection between two rooms via doors.
    
    Attributes:
        from_room_id: ID of source room
        to_room_id: ID of destination room
        from_door_pos: (x, y) position of door in source room
        to_door_pos: (x, y) position of door in destination room
    """
    from_room_id: str
    to_room_id: str
    from_door_pos: Tuple[int, int]
    to_door_pos: Tuple[int, int]


@dataclass
class LevelData:
    """
    Represents a complete multi-room level.
    
    Attributes:
        rooms: Dictionary mapping room IDs to RoomData objects
        door_links: List of connections between rooms
        internal_graph: Adjacency list of room connections
        start_room_id: ID of the starting room
        goal_room_id: ID of the final/goal room
        level_seed: Random seed used for generation
    """
    rooms: Dict[str, RoomData] = field(default_factory=dict)
    door_links: List[DoorLink] = field(default_factory=list)
    internal_graph: Dict[str, List[str]] = field(default_factory=dict)
    start_room_id: Optional[str] = None
    goal_room_id: Optional[str] = None
    level_seed: Optional[int] = None
    
    def get_room(self, room_id: str) -> Optional[RoomData]:
        """Get room by ID."""
        return self.rooms.get(room_id)
    
    def add_room(self, room_id: str, room: RoomData) -> None:
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
    """
    num_rooms: int = 5
    layout_type: str = "linear"  # "linear", "branching", "looping"
    branch_probability: float = 0.3
    loop_probability: float = 0.2
