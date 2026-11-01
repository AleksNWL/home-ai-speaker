// Parametric draft enclosure for home-ai-speaker
// Units: millimeters. Export STL from OpenSCAD after tuning.

wall = 2.4;
inner_w = 160;
inner_d = 110;
inner_h = 70;
screen_w = 120;
screen_h = 75;
screen_bezel = 3;
vent_slot_w = 3;
vent_slot_h = 18;
corner_r = 6;

module rounded_box(w, d, h, r) {
  hull() {
    for (x = [r, w - r])
      for (y = [r, d - r])
        translate([x, y, 0])
          cylinder(h=h, r=r, $fn=32);
  }
}

module shell() {
  difference() {
    rounded_box(inner_w + 2 * wall, inner_d + 2 * wall, inner_h + wall, corner_r);
    translate([wall, wall, wall])
      rounded_box(inner_w, inner_d, inner_h + 1, corner_r - 1);

    // Screen window (front = Y min)
    translate([
      (inner_w + 2 * wall - screen_w) / 2,
      -0.1,
      wall + (inner_h - screen_h) / 2
    ])
      cube([screen_w, wall + 1, screen_h]);

    // Rear vents
    for (i = [0:5]) {
      translate([
        wall + 20 + i * 20,
        inner_d + wall - 0.1,
        wall + 15
      ])
        cube([vent_slot_w, wall + 1, vent_slot_h]);
    }

    // Cable pass (USB / power)
    translate([inner_w + wall - 1, wall + 20, wall + 8])
      cube([wall + 2, 28, 18]);
  }
}

shell();

// Optional: board placeholder (not printed — preview only)
%translate([wall + 30, wall + 25, wall + 2])
  cube([85, 56, 18]);
