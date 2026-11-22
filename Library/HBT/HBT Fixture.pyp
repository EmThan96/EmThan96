<?xml version="1.0" encoding="utf-8"?>
<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/2026/schemas/PythonPart.xsd">
    <Script>
        <Name>HBT\HBTFixture.py</Name>
        <Title>HBT Fixture</Title>
        <Version>1.0</Version>
        <ReadLastInput>True</ReadLastInput>
    </Script>
    <Constants>
        <Constant>
            <Name>REF_POINT</Name>
            <Value>1</Value>
            <ValueType>Integer</ValueType>
        </Constant>
        <Constant>
            <Name>DIR_POINT</Name>
            <Value>2</Value>
            <ValueType>Integer</ValueType>
        </Constant>
    </Constants>
    <Page>
        <Name>HBTPage</Name>
        <Text>HBT</Text>
        <Parameters>
            <Parameter>
                <Name>ProductExp</Name>
                <Text>Product</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>Rows</Name>
                        <Text>Rebar rows</Text>
                        <Value>1</Value>
                        <ValueType>RadioButtonGroup</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>RowsSingle</Name>
                                <Text>Single-row</Text>
                                <Value>1</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                            <Parameter>
                                <Name>RowsDouble</Name>
                                <Text>Double-row</Text>
                                <Value>2</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                    <Parameter>
                        <Name>Casing</Name>
                        <Text>Casing type</Text>
                        <Value>HBT 85</Value>
                        <ValueType>StringComboBox</ValueType>
                        <ValueList>CasingList</ValueList>
                    </Parameter>
                    <Parameter>
                        <Name>RebarType</Name>
                        <Text>Rebar type</Text>
                        <Value>Type 1 - hook y (standard)</Value>
                        <ValueType>StringComboBox</ValueType>
                        <ValueList>RebarTypeList</ValueList>
                    </Parameter>
                    <Parameter>
                        <Name>Diameter</Name>
                        <Text>Rebar diameter [mm]</Text>
                        <Value>10</Value>
                        <ValueType>StringComboBox</ValueType>
                        <ValueList>DiameterList</ValueList>
                    </Parameter>
                    <Parameter>
                        <Name>Spacing</Name>
                        <Text>Rebar spacing s [cm]</Text>
                        <Value>15</Value>
                        <ValueType>StringComboBox</ValueType>
                        <ValueList>SpacingList</ValueList>
                    </Parameter>
                    <Parameter>
                        <Name>ElementLength</Name>
                        <Text>Element length L [mm]</Text>
                        <Value>1250</Value>
                        <ValueType>StringComboBox</ValueType>
                        <ValueList>LengthList</ValueList>
                    </Parameter>
                    <Parameter>
                        <Name>HBTStrip</Name>
                        <Text>HBT Strip (HBT-S)</Text>
                        <Value>False</Value>
                        <ValueType>CheckBox</ValueType>
                        <Visible>Rows == 2</Visible>
                    </Parameter>
                    <Parameter>
                        <Name>Article</Name>
                        <Text>Designation</Text>
                        <Value></Value>
                        <ValueType>String</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>DimExp</Name>
                <Text>Rebar dimensions</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>StandardDims</Name>
                        <Text>Standard dimensions</Text>
                        <Value>True</Value>
                        <ValueType>CheckBox</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>AnchorLength</Name>
                        <Text>h (component 1)</Text>
                        <Value>170</Value>
                        <ValueType>Length</ValueType>
                        <Enable>StandardDims == False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>ConnectionLength</Name>
                        <Text>lü (connected component)</Text>
                        <Value>390</Value>
                        <ValueType>Length</ValueType>
                        <Enable>StandardDims == False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>LegName</Name>
                        <Text>Leg name</Text>
                        <Value></Value>
                        <ValueType>String</ValueType>
                        <Enable>False</Enable>
                        <Visible>LegName != ""</Visible>
                    </Parameter>
                    <Parameter>
                        <Name>LegLength</Name>
                        <Text>Leg length (y / b / b1 / b2)</Text>
                        <Value>95</Value>
                        <ValueType>Length</ValueType>
                        <Enable>StandardDims == False</Enable>
                        <Visible>LegName != ""</Visible>
                    </Parameter>
                    <Parameter>
                        <Name>HMin</Name>
                        <Text>hmin</Text>
                        <Value>120</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>LuMax</Name>
                        <Text>lü,max</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>DataExp</Name>
                <Text>Catalogue data</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>CasingWidth</Name>
                        <Text>Casing width B</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>CasingDepth</Name>
                        <Text>Casing height H2</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>RebarWidth</Name>
                        <Text>Rebar width b</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                        <Visible>Rows == 2</Visible>
                    </Parameter>
                    <Parameter>
                        <Name>BarCount</Name>
                        <Text>Number of rebars</Text>
                        <Value>0</Value>
                        <ValueType>Integer</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>EndSpacing</Name>
                        <Text>End spacing a</Text>
                        <Value>0</Value>
                        <ValueType>Length</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>InfoText</Name>
                        <Text>Check</Text>
                        <Value></Value>
                        <ValueType>String</ValueType>
                        <Enable>False</Enable>
                    </Parameter>
                    <Parameter>
                        <Name>CatalogueFile</Name>
                        <Text>Catalogue file (empty = default)</Text>
                        <Value></Value>
                        <ValueType>String</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>PlacementExp</Name>
                <Text>Placement</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>FacePlane</Name>
                        <Text>Formwork face</Text>
                        <Value>2</Value>
                        <ValueType>RadioButtonGroup</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>FaceHorizontal</Name>
                                <Text>Horizontal face</Text>
                                <Value>1</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                            <Parameter>
                                <Name>FaceVerticalBoxHoriz</Name>
                                <Text>Vertical face, box horizontal</Text>
                                <Value>2</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                            <Parameter>
                                <Name>FaceVerticalBoxVert</Name>
                                <Text>Vertical face, box vertical</Text>
                                <Value>3</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                    <Parameter>
                        <Name>FlipSide</Name>
                        <Text>Flip anchor side</Text>
                        <Value>False</Value>
                        <ValueType>CheckBox</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>BarState</Name>
                        <Text>Bar state</Text>
                        <Value>1</Value>
                        <ValueType>RadioButtonGroup</ValueType>
                        <Parameters>
                            <Parameter>
                                <Name>BarsStraightened</Name>
                                <Text>Straightened (installed)</Text>
                                <Value>1</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                            <Parameter>
                                <Name>BarsDelivered</Name>
                                <Text>Bent in box (delivered)</Text>
                                <Value>2</Value>
                                <ValueType>RadioButton</ValueType>
                            </Parameter>
                        </Parameters>
                    </Parameter>
                    <Parameter>
                        <Name>CutBoxVolume</Name>
                        <Text>Cut box volume from precast element</Text>
                        <Value>False</Value>
                        <ValueType>CheckBox</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
            <Parameter>
                <Name>FormatExp</Name>
                <Text>Format</Text>
                <ValueType>Expander</ValueType>
                <Parameters>
                    <Parameter>
                        <Name>CommonProp</Name>
                        <Text></Text>
                        <Value></Value>
                        <ValueType>CommonProperties</ValueType>
                    </Parameter>
                    <Parameter>
                        <Name>BarColor</Name>
                        <Text>Bar color</Text>
                        <Value>6</Value>
                        <ValueType>Color</ValueType>
                    </Parameter>
                </Parameters>
            </Parameter>
        </Parameters>
    </Page>
    <Page>
        <Name>__HiddenPage__</Name>
        <Text/>
        <Parameters>
            <Parameter>
                <Name>InputMode</Name>
                <Value>1</Value>
                <ValueType>Integer</ValueType>
            </Parameter>
            <Parameter>
                <Name>CasingList</Name>
                <Value>HBT 85</Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>RebarTypeList</Name>
                <Value>Type 1 - hook y (standard)</Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>DiameterList</Name>
                <Value>10</Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>SpacingList</Name>
                <Value>15</Value>
                <ValueType>String</ValueType>
            </Parameter>
            <Parameter>
                <Name>LengthList</Name>
                <Value>1250</Value>
                <ValueType>String</ValueType>
            </Parameter>
        </Parameters>
    </Page>
</Element>
