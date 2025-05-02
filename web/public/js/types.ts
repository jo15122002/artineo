// types.ts
export interface RFIDData {
    uid1: string;
    uid2: string;
    uid3: string;
    current_set: number;
    button_pressed: boolean;
  }
  
  export interface RFIDMessage {
    module: number;
    action: 'set';
    data: RFIDData;
  }  