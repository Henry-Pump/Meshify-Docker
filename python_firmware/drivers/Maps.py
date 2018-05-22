"""Holds map values for advvfdipp."""

adv_vfd_ipp_map = {
  'pid_controlmode': {
      0: "Flow",
      1: "Fluid Level",
      2: "Tubing Pressure",
      3: "Manual"
  },

  'device_status': {
      0: "Running",
      1: "Pumped Off",
      2: "Alarmed",
      3: "Locked Out",
      4: "Stopped"
  },

  'dh_sensor_status': {
      0: "OK",
      1: "Connecting",
      2: "Open Circuit",
      3: "Shorted",
      4: "Cannot Decode"
  },

  'alarm': {0: "OK", 1: "Alarmed"},
  'lockout': {0: "OK", 1: "Locked Out"},
  'permissive': {
      0: "OK",
      1: "Flow",
      2: "Intake Pressure",
      3: "Intake Temperature",
      4: "Tubing Pressure",
      5: "VFD",
      6: "Fluid Level",
      7: "Min. Downtime"
  },

  'completion_parameter': {
      0: "Disabled",
      1: "Flow Total",
      2: "Flow Rate",
      3: "Intake Pressure",
      4: "Tubing Pressure",
      5: "Time",
  },
  'completion_comparison': {0: ">", 1: "<"}
}
