import { Component, OnInit } from '@angular/core';
import { ApiService } from "../services/api.service";
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-health-check',
  imports: [CommonModule],
  standalone: true,
  templateUrl: './health-check.html',
  styleUrls: ['./health-check.css']
})
export class HealthCheck implements OnInit {
  upTime: any;
  version: any;

  constructor(private api: ApiService) {}

  ngOnInit() {
     this.api.getHealthCheck().subscribe((data) => {
      this.upTime = data.upTime;
      this.version = data.version;
      console.log(data);
    });
  }


}