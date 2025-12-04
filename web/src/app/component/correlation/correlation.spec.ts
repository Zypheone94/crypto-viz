import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Correlation } from './correlation';

describe('Correlation', () => {
  let component: Correlation;
  let fixture: ComponentFixture<Correlation>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Correlation]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Correlation);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
